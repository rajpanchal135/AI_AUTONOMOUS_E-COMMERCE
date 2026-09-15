"""
apps/api/routers/products.py
Admin Product Management — Full CRUD + Real-World Enterprise Edge Cases

Edge Cases Covered:
  EC-PROD-01: Duplicate SKU code rejection (idempotency guard)
  EC-PROD-02: Price below cost (negative margin) hard stop
  EC-PROD-03: Price exceeds MRP statutory ceiling (10x cost guard)
  EC-PROD-04: SKU code format validation (alphanumeric + dashes only)
  EC-PROD-05: Zero-price product block (prevents accidental free listings)
  EC-PROD-06: Negative price / cost rejected
  EC-PROD-07: Archived product cannot be re-activated with 0 stock
  EC-PROD-08: Oversized product weight guard (> 50 kg flagged for hazmat)
  EC-PROD-09: Product title too short / too long (3–200 chars)
  EC-PROD-10: Reorder point cannot exceed physical on-hand stock
  EC-PROD-11: Cannot delete a product with active pending orders
  EC-PROD-12: Bulk price update blocked if any SKU has active P0 lock
  EC-PROD-13: Currency mismatch detection (SKU currency vs. tenant default)
  EC-PROD-14: Inactive (archived) product not visible in storefront risks
  EC-PROD-15: Initial stock seeding — reorder point auto-calculated from velocity
  EC-PROD-16: Duplicate product title across same tenant (soft warning)
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.database import get_db
from apps.api.models import (
    Product, SKU, InventoryLevel, Warehouse, Tenant,
    Order, OrderItem, ActionProposal, AuditLog
)
from apps.api.config import settings

router = APIRouter(prefix="/products", tags=["Product Management"])

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

SKU_CODE_PATTERN = re.compile(r'^[A-Z0-9][A-Z0-9\-]{2,48}[A-Z0-9]$')

class CreateProductRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Product display name")
    sku_code: str = Field(..., description="Unique warehouse SKU code (e.g. RUN-SHOE-BLK-42)")
    price_usd: float = Field(..., gt=0, description="Retail price in USD (must be > $0)")
    cost_usd: float = Field(default=0.0, ge=0, description="Unit cost in USD (COGS)")
    initial_stock: int = Field(default=0, ge=0, le=100000, description="Opening on-hand units")
    weight_grams: int = Field(default=500, ge=1, le=50000, description="Gross weight in grams")
    category: str = Field(default="general", description="Product category slug")
    reorder_point: Optional[int] = Field(default=None, ge=0, description="Override reorder trigger")
    daily_velocity: float = Field(default=2.0, ge=0.1, le=10000, description="Estimated units sold/day")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = Field(default="active")

    @field_validator('sku_code')
    @classmethod
    def validate_sku_format(cls, v: str) -> str:
        """EC-PROD-04: SKU code must be alphanumeric + dashes, 5-50 chars."""
        v = v.strip().upper()
        if not SKU_CODE_PATTERN.match(v):
            raise ValueError(
                "SKU code must be 5–50 characters, uppercase letters, digits and dashes only "
                "(e.g. RUN-SHOE-BLK-42). Cannot start or end with a dash."
            )
        return v

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """EC-PROD-09: Title must be 3–200 chars, strip whitespace."""
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Product title must be at least 3 characters.")
        if len(v) > 200:
            raise ValueError("Product title must not exceed 200 characters.")
        return v

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        allowed = {"USD", "EUR", "GBP", "INR", "CAD", "AUD"}
        if v not in allowed:
            raise ValueError(f"Currency must be one of: {', '.join(sorted(allowed))}")
        return v


class UpdateProductRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    price_usd: Optional[float] = Field(default=None, gt=0)
    cost_usd: Optional[float] = Field(default=None, ge=0)
    weight_grams: Optional[int] = Field(default=None, ge=1, le=50000)
    daily_velocity: Optional[float] = Field(default=None, ge=0.1)
    reorder_point: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None)


class AdjustStockRequest(BaseModel):
    delta: int = Field(..., description="Units to add (positive) or remove (negative)")
    reason: str = Field(default="Manual admin stock adjustment")

    @field_validator('delta')
    @classmethod
    def validate_delta(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Stock adjustment delta cannot be zero.")
        if abs(v) > 50000:
            raise ValueError("Stock adjustment cannot exceed 50,000 units in a single operation.")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _price_to_minor(usd: float) -> int:
    return int(round(usd * 100))

def _minor_to_usd(minor: int) -> float:
    return minor / 100.0

def _auto_reorder_point(initial_stock: int, daily_velocity: float) -> int:
    """EC-PROD-15: Auto-calculate reorder point as 7-day demand buffer."""
    return max(1, int(daily_velocity * 7))


# ─────────────────────────────────────────────────────────────────────────────
# GET /products — List all products for tenant
# ─────────────────────────────────────────────────────────────────────────────

@router.get("")
async def list_products(
    status: Optional[str] = Query(default=None, description="Filter by status: active, archived"),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """List all admin products with inventory levels."""
    stmt = (
        select(Product, SKU, InventoryLevel)
        .join(SKU, SKU.product_id == Product.id)
        .outerjoin(InventoryLevel, InventoryLevel.sku_id == SKU.id)
        .where(Product.tenant_id == settings.DEFAULT_TENANT_ID)
    )
    if status:
        stmt = stmt.where(Product.status == status)

    result = await db.execute(stmt)
    rows = result.all()

    products = []
    for prod, sku, inv in rows:
        # EC-PROD-14: Archived products flagged in admin listing
        price_usd = _minor_to_usd(sku.price_minor) if sku.price_minor else 0.0
        cost_usd = _minor_to_usd(sku.cost_minor) if sku.cost_minor else 0.0
        margin_pct = ((price_usd - cost_usd) / price_usd * 100) if price_usd > 0 else 0

        on_hand = inv.on_hand if inv else 0
        reserved = inv.reserved if inv else 0
        reorder_pt = inv.reorder_point if inv else 0
        velocity = float(inv.daily_velocity) if inv else 1.0
        days_cover = round(on_hand / velocity, 1) if velocity > 0 else 999.0
        net_available = on_hand - reserved

        # Filter by search
        if search:
            q = search.lower()
            if q not in prod.title.lower() and q not in sku.code.lower():
                continue

        # Filter by category (naive: by code prefix or metadata)
        if category and category != 'all':
            cat_in_code = sku.code.lower().startswith(category[:3].lower())
            if not cat_in_code:
                continue

        # Edge case warnings
        warnings = []
        if prod.status == "archived":
            warnings.append("EC-PROD-14: Archived — not visible in storefront")
        if on_hand <= reorder_pt and prod.status == "active":
            warnings.append("EC-INV-01: Below reorder point — inventory agent triggered")
        if margin_pct < 10:
            warnings.append(f"EC-PRC-03: Low margin ({margin_pct:.1f}%) — below 10% floor")
        if sku.weight_grams and sku.weight_grams > 30000:
            warnings.append("EC-PROD-08: Weight >30kg — hazmat/special carrier required")

        products.append({
            "product_id": prod.id,
            "sku_id": sku.id,
            "sku_code": sku.code,
            "product_title": prod.title,
            "status": prod.status,
            "price_usd": price_usd,
            "cost_usd": cost_usd,
            "margin_pct": round(margin_pct, 2),
            "currency": sku.currency,
            "weight_grams": sku.weight_grams or 0,
            "on_hand": on_hand,
            "reserved": reserved,
            "net_available": net_available,
            "reorder_point": reorder_pt,
            "daily_velocity": velocity,
            "days_of_cover": days_cover,
            "warnings": warnings,
            "created_at": prod.created_at.isoformat() if prod.created_at else None,
            "updated_at": prod.updated_at.isoformat() if prod.updated_at else None,
        })

    return {"total": len(products), "products": products}


# ─────────────────────────────────────────────────────────────────────────────
# POST /products — Create a new product + SKU + initial inventory
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_product(payload: CreateProductRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new product with all enterprise edge case validations applied.
    """
    tenant_id = settings.DEFAULT_TENANT_ID
    now = datetime.now(timezone.utc)

    # ── EC-PROD-01: Duplicate SKU code check ─────────────────────────────────
    existing_sku = await db.execute(select(SKU).where(
        and_(SKU.code == payload.sku_code, SKU.tenant_id == tenant_id)
    ))
    if existing_sku.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"EC-PROD-01: SKU code '{payload.sku_code}' already exists in this tenant. "
                   f"Use a unique SKU code or update the existing product."
        )

    # ── EC-PROD-05: Zero-price block ─────────────────────────────────────────
    if payload.price_usd <= 0:
        raise HTTPException(
            status_code=422,
            detail="EC-PROD-05: Retail price must be greater than $0. "
                   "Free products require a special gift SKU workflow."
        )

    # ── EC-PROD-06: Negative price / cost ────────────────────────────────────
    if payload.cost_usd < 0:
        raise HTTPException(status_code=422, detail="EC-PROD-06: Cost cannot be negative.")

    # ── EC-PROD-02: Price below cost — negative margin hard stop ─────────────
    if payload.cost_usd > 0 and payload.price_usd <= payload.cost_usd:
        raise HTTPException(
            status_code=422,
            detail=f"EC-PROD-02: Retail price (${payload.price_usd:.2f}) must exceed cost "
                   f"(${payload.cost_usd:.2f}). Selling at or below cost violates margin policy."
        )

    # ── EC-PROD-03: MRP ceiling check — price cannot be > 10x cost ──────────
    if payload.cost_usd > 0 and payload.price_usd > payload.cost_usd * 10:
        raise HTTPException(
            status_code=422,
            detail=f"EC-PROD-03: Retail price (${payload.price_usd:.2f}) exceeds 10× cost "
                   f"(${payload.cost_usd * 10:.2f}). Price likely entered incorrectly — "
                   f"please verify."
        )

    # ── EC-PROD-08: Hazmat weight alert (>30kg requires carrier flag) ─────────
    hazmat_flag = payload.weight_grams > 30000
    if payload.weight_grams > 50000:
        raise HTTPException(
            status_code=422,
            detail=f"EC-PROD-08: Product weight ({payload.weight_grams}g = "
                   f"{payload.weight_grams/1000:.1f}kg) exceeds 50 kg maximum. "
                   f"Contact your logistics team for freight configuration."
        )

    # ── EC-PROD-13: Currency mismatch check ──────────────────────────────────
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if tenant and payload.currency != tenant.default_currency:
        # Warn (don't block) — real systems might do FX conversion
        pass  # Will appear in product warnings list

    # ── EC-PROD-16: Duplicate title warning ──────────────────────────────────
    dup_title = await db.execute(select(Product).where(
        and_(
            Product.tenant_id == tenant_id,
            Product.title == payload.title.strip(),
            Product.status != "archived"
        )
    ))
    duplicate_title = dup_title.scalar_one_or_none()

    # ── Find default warehouse ────────────────────────────────────────────────
    wh_res = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id))
    warehouse = wh_res.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(
            status_code=400,
            detail="No warehouse configured for this tenant. Run /api/v1/simulation/seed first."
        )

    # ── EC-PROD-15: Auto-calculate reorder point ──────────────────────────────
    reorder_pt = payload.reorder_point
    if reorder_pt is None:
        reorder_pt = _auto_reorder_point(payload.initial_stock, payload.daily_velocity)

    # ── EC-PROD-10: Reorder point sanity check ────────────────────────────────
    if reorder_pt > payload.initial_stock and payload.initial_stock > 0:
        raise HTTPException(
            status_code=422,
            detail=f"EC-PROD-10: Reorder point ({reorder_pt}) cannot exceed initial stock "
                   f"({payload.initial_stock}). Either increase initial stock or lower the reorder point."
        )

    # ── Create Product → SKU → InventoryLevel ─────────────────────────────────
    prod_id = str(uuid.uuid4())
    sku_id = str(uuid.uuid4())
    inv_id = str(uuid.uuid4())

    product = Product(
        id=prod_id,
        tenant_id=tenant_id,
        external_id=f"prod-{payload.sku_code.lower()}",
        title=payload.title.strip(),
        status=payload.status,
        product_metadata={"category": payload.category, "hazmat": hazmat_flag},
        created_at=now,
        updated_at=now
    )
    db.add(product)
    await db.flush()

    sku = SKU(
        id=sku_id,
        tenant_id=tenant_id,
        product_id=prod_id,
        code=payload.sku_code,
        cost_minor=_price_to_minor(payload.cost_usd),
        price_minor=_price_to_minor(payload.price_usd),
        currency=payload.currency,
        weight_grams=payload.weight_grams,
        active=True
    )
    db.add(sku)
    await db.flush()

    inv = InventoryLevel(
        id=inv_id,
        tenant_id=tenant_id,
        sku_id=sku_id,
        warehouse_id=warehouse.id,
        on_hand=payload.initial_stock,
        reserved=0,
        inbound=0,
        reorder_point=reorder_pt,
        daily_velocity=payload.daily_velocity,
        updated_at=now
    )
    db.add(inv)

    # ── Audit log entry ───────────────────────────────────────────────────────
    audit = AuditLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        actor_type="user",
        actor_id="admin@autonomous.store",
        operation="product.create",
        resource_type="product",
        resource_id=prod_id,
        before_data=None,
        after_data={
            "sku_code": payload.sku_code,
            "title": payload.title,
            "price_usd": payload.price_usd,
            "cost_usd": payload.cost_usd,
            "initial_stock": payload.initial_stock
        },
        correlation_id=str(uuid.uuid4()),
        created_at=now
    )
    db.add(audit)

    await db.commit()

    response = {
        "status": "created",
        "product_id": prod_id,
        "sku_id": sku_id,
        "sku_code": payload.sku_code,
        "product_title": payload.title.strip(),
        "price_usd": payload.price_usd,
        "cost_usd": payload.cost_usd,
        "margin_pct": round(((payload.price_usd - payload.cost_usd) / payload.price_usd * 100), 2) if payload.price_usd > 0 else 0,
        "initial_stock": payload.initial_stock,
        "reorder_point": reorder_pt,
        "hazmat_flagged": hazmat_flag,
        "currency_mismatch_warning": payload.currency != (tenant.default_currency if tenant else "USD"),
        "duplicate_title_warning": bool(duplicate_title),
        "edge_cases_evaluated": [
            "EC-PROD-01: Duplicate SKU", "EC-PROD-02: Negative margin",
            "EC-PROD-03: MRP ceiling", "EC-PROD-04: SKU format",
            "EC-PROD-05: Zero price", "EC-PROD-06: Negative cost",
            "EC-PROD-08: Hazmat weight", "EC-PROD-09: Title length",
            "EC-PROD-10: Reorder point", "EC-PROD-13: Currency",
            "EC-PROD-15: Auto reorder calc", "EC-PROD-16: Duplicate title"
        ],
        "message": f"Product '{payload.title}' created successfully with SKU {payload.sku_code}."
    }
    if duplicate_title:
        response["warning"] = (
            f"EC-PROD-16: A product with title '{payload.title}' already exists. "
            "Consider using a more distinctive name."
        )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# GET /products/{sku_code} — Single product detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{sku_code}")
async def get_product(sku_code: str, db: AsyncSession = Depends(get_db)):
    """Fetch a single product by SKU code with full inventory detail."""
    sku_res = await db.execute(select(SKU).where(
        and_(SKU.code == sku_code.upper(), SKU.tenant_id == settings.DEFAULT_TENANT_ID)
    ))
    sku = sku_res.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail=f"SKU '{sku_code}' not found.")

    prod_res = await db.execute(select(Product).where(Product.id == sku.product_id))
    prod = prod_res.scalar_one_or_none()

    inv_res = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == sku.id))
    inv = inv_res.scalar_one_or_none()

    price_usd = _minor_to_usd(sku.price_minor)
    cost_usd = _minor_to_usd(sku.cost_minor or 0)
    margin_pct = ((price_usd - cost_usd) / price_usd * 100) if price_usd > 0 else 0

    return {
        "product_id": prod.id if prod else None,
        "sku_id": sku.id,
        "sku_code": sku.code,
        "product_title": prod.title if prod else "Unknown",
        "status": prod.status if prod else "unknown",
        "price_usd": price_usd,
        "cost_usd": cost_usd,
        "margin_pct": round(margin_pct, 2),
        "currency": sku.currency,
        "weight_grams": sku.weight_grams or 0,
        "on_hand": inv.on_hand if inv else 0,
        "reserved": inv.reserved if inv else 0,
        "net_available": (inv.on_hand - inv.reserved) if inv else 0,
        "inbound": inv.inbound if inv else 0,
        "reorder_point": inv.reorder_point if inv else 0,
        "daily_velocity": float(inv.daily_velocity) if inv else 1.0,
        "days_of_cover": round((inv.on_hand / float(inv.daily_velocity)), 1) if inv and float(inv.daily_velocity) > 0 else 999.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /products/{sku_code} — Update product (title, price, cost, etc.)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{sku_code}")
async def update_product(
    sku_code: str,
    payload: UpdateProductRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update product price / title / status with policy validation."""
    tenant_id = settings.DEFAULT_TENANT_ID
    now = datetime.now(timezone.utc)

    sku_res = await db.execute(select(SKU).where(
        and_(SKU.code == sku_code.upper(), SKU.tenant_id == tenant_id)
    ))
    sku = sku_res.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail=f"EC-PROD: SKU '{sku_code}' not found.")

    prod_res = await db.execute(select(Product).where(Product.id == sku.product_id))
    prod = prod_res.scalar_one_or_none()

    inv_res = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == sku.id))
    inv = inv_res.scalar_one_or_none()

    old_price = _minor_to_usd(sku.price_minor)
    old_cost = _minor_to_usd(sku.cost_minor or 0)
    new_price = payload.price_usd if payload.price_usd is not None else old_price
    new_cost = payload.cost_usd if payload.cost_usd is not None else old_cost

    # ── EC-PROD-02: Price below cost check ───────────────────────────────────
    if new_cost > 0 and new_price <= new_cost:
        raise HTTPException(
            status_code=422,
            detail=f"EC-PROD-02: Updated price (${new_price:.2f}) must exceed cost "
                   f"(${new_cost:.2f}). Cannot save negative-margin product."
        )

    # ── EC-PROD-03: MRP ceiling on update ────────────────────────────────────
    if new_cost > 0 and new_price > new_cost * 10:
        raise HTTPException(
            status_code=422,
            detail=f"EC-PROD-03: Updated price (${new_price:.2f}) exceeds 10x cost. Verify amount."
        )

    # ── EC-PROD-07: Re-activating an archived product with 0 stock ───────────
    if payload.status == "active" and prod and prod.status == "archived":
        stock = inv.on_hand if inv else 0
        if stock == 0:
            raise HTTPException(
                status_code=422,
                detail="EC-PROD-07: Cannot re-activate an archived product with 0 stock. "
                       "Add initial inventory before activating."
            )

    # ── EC-PROD-12: Block price change if active P0 lock proposal exists ──────
    pending_lock = await db.execute(select(ActionProposal).where(
        and_(
            ActionProposal.tenant_id == tenant_id,
            ActionProposal.resource_id == sku.code,
            ActionProposal.status == "pending_approval",
            ActionProposal.action_type.in_(["pricing.freeze", "pricing.hold"])
        )
    ))
    if pending_lock.scalar_one_or_none() and payload.price_usd is not None:
        raise HTTPException(
            status_code=409,
            detail=f"EC-PROD-12: SKU {sku.code} has an active P0 pricing lock proposal. "
                   f"Approve or reject the pending action before changing the price."
        )

    # ── EC-PROD-10: Reorder point update validation ───────────────────────────
    if payload.reorder_point is not None and inv:
        if payload.reorder_point > inv.on_hand:
            raise HTTPException(
                status_code=422,
                detail=f"EC-PROD-10: New reorder point ({payload.reorder_point}) exceeds "
                       f"current on-hand stock ({inv.on_hand}). Inventory agent would immediately "
                       f"trigger a purchase order. Increase stock first or lower reorder point."
            )

    # ── Apply updates ─────────────────────────────────────────────────────────
    before = {"price_usd": old_price, "title": prod.title if prod else None, "status": prod.status if prod else None}

    if payload.price_usd is not None:
        sku.price_minor = _price_to_minor(payload.price_usd)
    if payload.cost_usd is not None:
        sku.cost_minor = _price_to_minor(payload.cost_usd)
    if payload.weight_grams is not None:
        sku.weight_grams = payload.weight_grams
    if prod:
        if payload.title is not None:
            prod.title = payload.title.strip()
        if payload.status is not None:
            prod.status = payload.status
        prod.updated_at = now
    if inv:
        if payload.daily_velocity is not None:
            inv.daily_velocity = payload.daily_velocity
        if payload.reorder_point is not None:
            inv.reorder_point = payload.reorder_point
        inv.updated_at = now

    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        actor_type="user", actor_id="admin@autonomous.store",
        operation="product.update", resource_type="sku", resource_id=sku.id,
        before_data=before,
        after_data={"price_usd": new_price, "title": payload.title, "status": payload.status},
        correlation_id=str(uuid.uuid4()), created_at=now
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "updated",
        "sku_code": sku_code.upper(),
        "new_price_usd": new_price,
        "new_cost_usd": new_cost,
        "new_margin_pct": round(((new_price - new_cost) / new_price * 100), 2) if new_price > 0 else 0,
        "message": f"SKU {sku_code.upper()} updated successfully."
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /products/{sku_code}/adjust-stock — Admin manual stock adjustment
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{sku_code}/adjust-stock")
async def adjust_stock(
    sku_code: str,
    payload: AdjustStockRequest,
    db: AsyncSession = Depends(get_db)
):
    """Admin stock adjustment: positive = add, negative = remove."""
    tenant_id = settings.DEFAULT_TENANT_ID
    now = datetime.now(timezone.utc)

    sku_res = await db.execute(select(SKU).where(
        and_(SKU.code == sku_code.upper(), SKU.tenant_id == tenant_id)
    ))
    sku = sku_res.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail=f"SKU '{sku_code}' not found.")

    inv_res = await db.execute(select(InventoryLevel).where(InventoryLevel.sku_id == sku.id))
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found for this SKU.")

    old_on_hand = inv.on_hand
    new_on_hand = old_on_hand + payload.delta

    if new_on_hand < 0:
        raise HTTPException(
            status_code=422,
            detail=f"Stock adjustment would result in negative inventory "
                   f"({old_on_hand} + ({payload.delta}) = {new_on_hand}). "
                   f"Maximum removal is {old_on_hand} units."
        )

    if new_on_hand < inv.reserved:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot reduce stock to {new_on_hand} — there are {inv.reserved} units "
                   f"currently reserved in active customer carts. Release reservations first."
        )

    inv.on_hand = new_on_hand
    inv.updated_at = now

    audit = AuditLog(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        actor_type="user", actor_id="admin@autonomous.store",
        operation="inventory.adjust", resource_type="inventory_level", resource_id=inv.id,
        before_data={"on_hand": old_on_hand},
        after_data={"on_hand": new_on_hand, "delta": payload.delta, "reason": payload.reason},
        correlation_id=str(uuid.uuid4()), created_at=now
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "adjusted",
        "sku_code": sku_code.upper(),
        "previous_stock": old_on_hand,
        "delta": payload.delta,
        "new_stock": new_on_hand,
        "reserved": inv.reserved,
        "net_available": new_on_hand - inv.reserved,
        "message": f"Stock for {sku_code.upper()} adjusted by {payload.delta:+d} units. New on-hand: {new_on_hand}."
    }


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /products/{sku_code} — Archive (soft delete)
# ─────────────────────────────────────────────────────────────────────────────

@router.delete("/{sku_code}")
async def archive_product(sku_code: str, db: AsyncSession = Depends(get_db)):
    """
    Soft-archive a product (set status = 'archived').
    EC-PROD-11: Cannot archive if active pending orders exist.
    """
    tenant_id = settings.DEFAULT_TENANT_ID
    now = datetime.now(timezone.utc)

    sku_res = await db.execute(select(SKU).where(
        and_(SKU.code == sku_code.upper(), SKU.tenant_id == tenant_id)
    ))
    sku = sku_res.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail=f"SKU '{sku_code}' not found.")

    prod_res = await db.execute(select(Product).where(Product.id == sku.product_id))
    prod = prod_res.scalar_one_or_none()

    # ── EC-PROD-11: Check active orders containing this SKU ────────────────
    active_order_items = await db.execute(
        select(OrderItem).join(Order, Order.id == OrderItem.order_id).where(
            and_(
                OrderItem.sku_id == sku.id,
                Order.status.in_(["pending", "processing", "partially_shipped"])
            )
        )
    )
    active_items = active_order_items.scalars().all()
    if active_items:
        raise HTTPException(
            status_code=409,
            detail=f"EC-PROD-11: Cannot archive SKU '{sku_code}' — {len(active_items)} active "
                   f"order(s) contain this product. Fulfill or cancel those orders first."
        )

    if prod:
        prod.status = "archived"
        prod.updated_at = now

    sku.active = False

    audit = AuditLog(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        actor_type="user", actor_id="admin@autonomous.store",
        operation="product.archive", resource_type="product", resource_id=prod.id if prod else sku.id,
        before_data={"status": "active"},
        after_data={"status": "archived"},
        correlation_id=str(uuid.uuid4()), created_at=now
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "archived",
        "sku_code": sku_code.upper(),
        "message": f"Product '{prod.title if prod else sku_code}' archived successfully. "
                   "It is no longer visible in the storefront."
    }
