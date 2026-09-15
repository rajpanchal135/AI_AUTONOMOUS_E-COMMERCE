import math
from typing import Dict, Any

def calculate_inventory_metrics(
    on_hand: int,
    reserved: int,
    inbound: int,
    daily_velocity: float,
    lead_time_days: int = 7,
    service_factor: float = 1.65,  # 95% service level factor
    demand_stddev: float = 2.0,
    target_days_cover: int = 45,
    min_order_qty: int = 50,
    pack_size: int = 10
) -> Dict[str, Any]:
    """
    Deterministic inventory calculations as specified in Section 6.2 of the blueprint.
    Uses classical safety-stock and lead-time demand formulas.
    """
    net_available = on_hand + inbound - reserved
    days_of_cover = round(net_available / daily_velocity, 1) if daily_velocity > 0 else 999.0
    lead_time_demand = daily_velocity * lead_time_days
    safety_stock = math.ceil(service_factor * demand_stddev * math.sqrt(lead_time_days))
    reorder_point = math.ceil(lead_time_demand + safety_stock)
    
    is_low_stock = net_available <= reorder_point
    raw_qty = max(0, (target_days_cover * daily_velocity) - net_available)
    
    # Apply MOQ and pack size rounding
    order_qty = max(min_order_qty, raw_qty) if is_low_stock else 0
    if order_qty > 0 and pack_size > 0:
        order_qty = math.ceil(order_qty / pack_size) * pack_size

    return {
        "net_available": net_available,
        "days_of_cover": days_of_cover,
        "lead_time_demand": round(lead_time_demand, 1),
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "is_low_stock": is_low_stock,
        "recommended_reorder_qty": int(order_qty)
    }
