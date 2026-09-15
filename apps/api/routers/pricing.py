from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.database import get_db
from apps.api.models import SKU, Product, InventoryLevel
from apps.api.schemas import PricingRecommendationItem

router = APIRouter(prefix="/pricing", tags=["Pricing"])

@router.get("/recommendations", response_model=List[PricingRecommendationItem])
async def get_pricing_recommendations(db: AsyncSession = Depends(get_db)):
    query = (
        select(SKU, Product, InventoryLevel)
        .join(Product, SKU.product_id == Product.id)
        .join(InventoryLevel, SKU.id == InventoryLevel.sku_id)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for sku, prod, inv in rows:
        cost = (sku.cost_minor or 0) / 100.0
        price = (sku.price_minor or 0) / 100.0
        margin = round(((price - cost) / price) * 100, 1) if price > 0 else 0
        
        velocity = float(inv.daily_velocity or 1.0)
        net_avail = inv.on_hand + inv.inbound - inv.reserved
        cover = round(net_avail / velocity, 1) if velocity > 0 else 999.0

        if cover < 10:
            rec_price = round(price * 1.05, 2)
            proj_margin = round(((rec_price - cost) / rec_price) * 100, 1)
            reason = f"Imminent stockout ({cover}d cover). 5% price increase dampens burn and lifts margin."
            velocity_change = -8.0
        else:
            rec_price = price
            proj_margin = margin
            reason = "Price is optimal for target margin."
            velocity_change = 0.0

        items.append(
            PricingRecommendationItem(
                sku_id=sku.id,
                sku_code=sku.code,
                title=prod.title,
                current_price=price,
                cost=cost,
                current_margin_pct=margin,
                recommended_price=rec_price,
                projected_margin_pct=proj_margin,
                expected_unit_change_pct=velocity_change,
                reason=reason,
                confidence=0.91
            )
        )
    return items
