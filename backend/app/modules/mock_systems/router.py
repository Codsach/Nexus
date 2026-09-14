from fastapi import APIRouter
from app.modules.mock_systems import store

router = APIRouter(prefix="/mock", tags=["mock_systems"])


@router.get("/crm/{customer_id}")
async def get_crm(customer_id: str):
    record = store.get_crm(customer_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(404, f"Customer '{customer_id}' not found")
    return record.model_dump()


@router.get("/billing/{customer_id}")
async def get_billing(customer_id: str):
    record = store.get_billing(customer_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(404, f"No billing record for '{customer_id}'")
    return record.model_dump()


@router.get("/orders/{customer_id}")
async def get_orders(customer_id: str):
    orders = store.get_orders(customer_id)
    return [o.model_dump() for o in orders]


@router.get("/ticket-history/{customer_id}")
async def get_ticket_history(customer_id: str):
    history = store.get_ticket_history(customer_id)
    return [h.model_dump() for h in history]


@router.get("/customers")
async def list_customers():
    return store.list_all_customers()


@router.post("/reset")
async def reset_mock_data():
    counts = store.reset_all()
    return {"status": "reset", "records_loaded": counts}
