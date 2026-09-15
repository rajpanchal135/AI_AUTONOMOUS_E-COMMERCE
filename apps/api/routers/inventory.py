from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.database import get_db
from apps.api.models import SKU, Product, InventoryLevel, Supplier, InventoryReservation
from apps.api.schemas import InventoryRiskItem

router = APIRouter(prefix="/inventory", tags=["Inventory"])

RESERVATION_TTL_MINUTES = 15

class ReserveRequest(BaseModel):
    quantity: int = Field(default=1, gt=0, le=100, description="Quantity to reserve (1-100)")
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class RestockRequest(BaseModel):
    quantity: int = 150
    reason: str = "Manual emergency restock"

@router.get("/risks", response_model=List[InventoryRiskItem])
async def get_inventory_risks(db: AsyncSession = Depends(get_db)):
    query = (
        select(InventoryLevel, SKU, Product, Supplier)
        .join(SKU, InventoryLevel.sku_id == SKU.id)
        .join(Product, SKU.product_id == Product.id)
        .outerjoin(Supplier, SKU.tenant_id == Supplier.tenant_id)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for inv, sku, prod, sup in rows:
        net_avail = inv.on_hand + inv.inbound - inv.reserved
        velocity = float(inv.daily_velocity or 1.0)
        days_cover = round(net_avail / velocity, 1) if velocity > 0 else 999.0

        status = "healthy"
        if net_avail <= inv.reorder_point:
            status = "critical" if days_cover < 7 else "warning"

        items.append(
            InventoryRiskItem(
                sku_id=sku.id,
                sku_code=sku.code,
                product_title=prod.title,
                on_hand=inv.on_hand,
                reserved=inv.reserved,
                net_available=net_avail,
                reorder_point=inv.reorder_point,
                daily_velocity=velocity,
                days_of_cover=days_cover,
                status=status,
                supplier_name=sup.name if sup else "Primary Supplier",
                supplier_lead_time=sup.lead_time_days if sup else 12
            )
        )
    return items

@router.post("/{sku_code}/reserve")
async def reserve_stock(
    sku_code: str,
    payload: ReserveRequest = ReserveRequest(),
    db: AsyncSession = Depends(get_db)
):
    # 1. Clean up any expired reservations first
    now = datetime.now(timezone.utc)
    expired_stmt = select(InventoryReservation).where(
        and_(
            InventoryReservation.status == "active",
            InventoryReservation.expires_at <= now
        )
    )
    exp_res = await db.execute(expired_stmt)
    for exp in exp_res.scalars().all():
        exp.status = "expired"
        inv_item = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == exp.sku_id))
        inv_rec = inv_item.scalar_one_or_none()
        if inv_rec:
            inv_rec.reserved = max(0, inv_rec.reserved - exp.quantity)

    # 2. Find SKU
    sku_res = await db.execute(select(SKU).where(SKU.code == sku_code))
    sku = sku_res.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail=f"SKU {sku_code} not found")

    # 3. Find Inventory
    inv_res = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == sku.id))
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    net_available = inv.on_hand - inv.reserved
    if net_available < payload.quantity:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient available stock for {sku.code}. Available: {max(0, net_available)}, requested: {payload.quantity}"
        )

    # 4. Create time-bound reservation with locked price
    expires_at = now + timedelta(minutes=RESERVATION_TTL_MINUTES)
    res_id = str(uuid.uuid4())
    reservation = InventoryReservation(
        id=res_id,
        tenant_id=sku.tenant_id,
        sku_id=sku.id,
        user_id=payload.user_id,
        session_id=payload.session_id or res_id,
        quantity=payload.quantity,
        locked_price_minor=sku.price_minor,
        status="active",
        expires_at=expires_at,
        created_at=now
    )
    inv.reserved += payload.quantity
    db.add(reservation)
    await db.commit()

    return {
        "status": "reserved",
        "reservation_id": res_id,
        "sku_code": sku.code,
        "quantity": payload.quantity,
        "locked_price_minor": sku.price_minor,
        "currency": sku.currency,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": RESERVATION_TTL_MINUTES * 60,
        "message": f"Locked {payload.quantity} unit(s) of {sku.code} for {RESERVATION_TTL_MINUTES} minutes."
    }

@router.delete("/reservations/{reservation_id}")
async def release_reservation(reservation_id: str, db: AsyncSession = Depends(get_db)):
    res_stmt = select(InventoryReservation).where(InventoryReservation.id == reservation_id)
    res_result = await db.execute(res_stmt)
    reservation = res_result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.status == "active":
        reservation.status = "released"
        inv_item = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == reservation.sku_id))
        inv_rec = inv_item.scalar_one_or_none()
        if inv_rec:
            inv_rec.reserved = max(0, inv_rec.reserved - reservation.quantity)
        await db.commit()

    return {"status": "released", "reservation_id": reservation_id}

@router.post("/{sku_code}/restock")
async def restock_sku(sku_code: str, payload: RestockRequest = RestockRequest(), db: AsyncSession = Depends(get_db)):
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Restock quantity must be a positive integer greater than 0")
    if payload.quantity > 50000:
        raise HTTPException(status_code=400, detail="Restock quantity cannot exceed 50,000 units per operation")

    sku_res = await db.execute(select(SKU).where(SKU.code == sku_code))
    sku = sku_res.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail=f"SKU {sku_code} not found")

    inv_res = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == sku.id))
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    inv.on_hand += payload.quantity
    inv.reserved = 0
    await db.commit()

    return {
        "status": "success",
        "sku_code": sku_code,
        "restocked_quantity": payload.quantity,
        "new_on_hand": inv.on_hand,
        "message": f"Successfully restocked {payload.quantity} units of {sku.code}. New available stock: {inv.on_hand}."
    }
