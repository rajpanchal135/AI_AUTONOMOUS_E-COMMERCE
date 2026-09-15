from typing import List, Dict

EVENT_ROUTES: Dict[str, List[str]] = {
    "inventory.stock_low": ["inventory", "marketing", "pricing", "analytics"],
    "order.created": ["orders", "risk", "inventory", "pricing", "logistics", "support", "marketing", "analytics"],
    "order.placed": ["orders", "risk", "inventory", "pricing", "logistics", "support", "marketing", "analytics"],
    "order.shipment_delayed": ["logistics", "support", "orders"],
    "ticket.created": ["support", "orders"],
    "competitor.price_changed": ["pricing", "analytics"],
    "schedule.daily": ["analytics", "inventory", "orders", "marketing"],
    "simulation.demo": ["inventory", "marketing", "pricing", "orders", "logistics", "support", "analytics"]
}

def resolve_agents_for_event(event_type: str) -> List[str]:
    """
    Returns list of specialist agents to trigger for a given normalized event type.
    """
    return EVENT_ROUTES.get(event_type, ["analytics"])
