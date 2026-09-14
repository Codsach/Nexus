from fastapi import APIRouter
from app.modules.specialist_agents.billing.agent import BillingAgent
from app.modules.specialist_agents.order.agent import OrderAgent
from app.modules.specialist_agents.technical.agent import TechnicalAgent
from app.modules.specialist_agents.account.agent import AccountAgent
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.db.database import get_db

router = APIRouter(prefix="/specialist-agents", tags=["specialist_agents"])

AGENTS = {
    "billing": BillingAgent,
    "order": OrderAgent,
    "technical": TechnicalAgent,
    "account": AccountAgent,
}


class InvestigateRequest(BaseModel):
    ticket_id: str
    customer_id: str
    message: str


@router.post("/{domain}/investigate")
async def investigate(domain: str, req: InvestigateRequest):
    if domain not in AGENTS:
        from fastapi import HTTPException
        raise HTTPException(400, f"Unknown domain: {domain}. Valid: {list(AGENTS.keys())}")
    agent = AGENTS[domain]()
    finding = await agent.investigate(req.ticket_id, req.customer_id, req.message)
    return finding.model_dump()
