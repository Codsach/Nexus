"""
Mock Systems — in-memory store loaded from fixtures.
Provides the enterprise backend queries that specialist agents call.
POST /api/v1/mock/reset reloads all data from JSON files.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from app.shared.schemas.models import (
    CRMRecord, BillingRecord, BillingTransaction, OrderRecord, ShippingEvent, TicketHistoryRecord
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# In-memory stores (reloaded on reset)
# ---------------------------------------------------------------------------
_crm: dict[str, dict] = {}
_billing: dict[str, dict] = {}
_orders: dict[str, list[dict]] = {}
_ticket_history: list[dict] = []


def _load_all() -> None:
    global _crm, _billing, _orders, _ticket_history

    with open(FIXTURES_DIR / "crm.json") as f:
        customers = json.load(f)
        _crm = {c["customer_id"]: c for c in customers}

    with open(FIXTURES_DIR / "billing.json") as f:
        _billing = json.load(f)

    with open(FIXTURES_DIR / "orders.json") as f:
        _orders = json.load(f)

    with open(FIXTURES_DIR / "ticket_history.json") as f:
        _ticket_history = json.load(f)


# Load on import
_load_all()


# ---------------------------------------------------------------------------
# Query functions (called by specialist agents)
# ---------------------------------------------------------------------------

def get_crm(customer_id: str) -> CRMRecord | None:
    data = _crm.get(customer_id)
    if not data:
        return None
    return CRMRecord(**data)


def get_billing(customer_id: str) -> BillingRecord | None:
    data = _billing.get(customer_id)
    if not data:
        return None
    transactions = [BillingTransaction(**t) for t in data.get("transactions", [])]
    return BillingRecord(**{**data, "transactions": transactions})


def get_orders(customer_id: str) -> list[OrderRecord]:
    orders_data = _orders.get(customer_id, [])
    result = []
    for o in orders_data:
        events = [ShippingEvent(**e) for e in o.get("shipping_events", [])]
        result.append(OrderRecord(**{**o, "shipping_events": events}))
    return result


def get_ticket_history(customer_id: str) -> list[TicketHistoryRecord]:
    return [
        TicketHistoryRecord(**r)
        for r in _ticket_history
        if r["customer_id"] == customer_id
    ]


def get_all_ticket_history() -> list[TicketHistoryRecord]:
    return [TicketHistoryRecord(**r) for r in _ticket_history]


def reset_all() -> dict[str, int]:
    """Reset all in-memory stores to fixture state. Returns record counts."""
    _load_all()
    return {
        "crm": len(_crm),
        "billing": len(_billing),
        "orders": sum(len(v) for v in _orders.values()),
        "ticket_history": len(_ticket_history),
    }


def list_all_customers() -> list[dict]:
    return list(_crm.values())
