from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.shared.db.database import get_db, EscalationPacketORM, TicketORM

router = APIRouter(prefix="/escalation", tags=["escalation"])


@router.get("/tickets")
async def get_escalated_tickets(db: AsyncSession = Depends(get_db)):
    """Get all escalated tickets with their packets."""
    result = await db.execute(
        select(TicketORM).where(TicketORM.status == "escalated").order_by(TicketORM.created_at.desc())
    )
    tickets = result.scalars().all()

    packets_result = await db.execute(select(EscalationPacketORM))
    packets = {p.ticket_id: p for p in packets_result.scalars().all()}

    return [
        {
            "ticket_id": t.id,
            "customer_id": t.customer_id,
            "intent": t.intent,
            "urgency": t.urgency,
            "sentiment": t.sentiment,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "has_packet": t.id in packets,
        }
        for t in tickets
    ]


@router.get("/{ticket_id}/packet")
async def get_handoff_packet(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Get the handoff packet for an escalated ticket."""
    result = await db.execute(
        select(EscalationPacketORM).where(EscalationPacketORM.ticket_id == ticket_id)
    )
    packet = result.scalar_one_or_none()
    if not packet:
        raise HTTPException(404, f"No escalation packet for ticket {ticket_id}")

    return {
        "id": packet.id,
        "ticket_id": packet.ticket_id,
        "customer_id": packet.customer_id,
        "justification": packet.justification,
        "issue_summary": packet.issue_summary,
        "systems_checked": json.loads(packet.systems_checked_json),
        "findings_summary": json.loads(packet.findings_summary_json),
        "actions_attempted": json.loads(packet.actions_attempted_json),
        "customer_sentiment_trend": json.loads(packet.sentiment_trend_json),
        "recommended_next_step": packet.recommended_next_step,
        "priority": packet.priority,
        "created_at": packet.created_at.isoformat() if packet.created_at else None,
    }
