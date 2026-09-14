"""
Coordinator FastAPI router — ticket submission and SSE trace stream.
"""
from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.shared.db.database import get_db, TicketORM, AgentFindingORM
from app.shared.events import bus
from app.modules.coordinator import service

router = APIRouter(prefix="/coordinator", tags=["coordinator"])


class SubmitTicketRequest(BaseModel):
    customer_id: str
    message: str


@router.post("/tickets")
async def submit_ticket(
    req: SubmitTicketRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit a new support ticket. Processing runs in background; trace events stream via SSE."""
    ticket = await service.create_ticket(req.customer_id, req.message, db)

    # Process in background so SSE can stream immediately
    background_tasks.add_task(
        service.process_ticket,
        ticket.id,
        req.customer_id,
        req.message,
        db,
    )

    return {
        "ticket_id": ticket.id,
        "status": ticket.status.value,
        "message": "Ticket created. Connect to /trace for live updates.",
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Get ticket state and conversation."""
    result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")

    messages = json.loads(ticket.messages_json or "[]")

    # Get findings
    findings_result = await db.execute(
        select(AgentFindingORM).where(AgentFindingORM.ticket_id == ticket_id)
    )
    findings = findings_result.scalars().all()

    return {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "status": ticket.status,
        "intent": ticket.intent,
        "urgency": ticket.urgency,
        "sentiment": ticket.sentiment,
        "messages": messages,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
        "findings": [
            {
                "agent": f.agent_name,
                "summary": f.summary,
                "evidence": json.loads(f.evidence_json),
                "confidence": f.confidence,
                "actions": json.loads(f.actions_available_json),
                "root_cause": f.root_cause,
            }
            for f in findings
        ],
    }


@router.get("/tickets")
async def list_tickets(db: AsyncSession = Depends(get_db)):
    """List all tickets (for dashboard/escalation view)."""
    result = await db.execute(select(TicketORM).order_by(TicketORM.created_at.desc()))
    tickets = result.scalars().all()
    return [
        {
            "id": t.id,
            "customer_id": t.customer_id,
            "status": t.status,
            "intent": t.intent,
            "urgency": t.urgency,
            "sentiment": t.sentiment,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tickets
    ]


@router.get("/tickets/{ticket_id}/trace")
async def stream_trace(ticket_id: str):
    """SSE endpoint — streams reasoning trace events live for a ticket."""
    async def event_generator():
        async for event in bus.subscribe(ticket_id):
            data = {
                "id": event.id,
                "ticket_id": event.ticket_id,
                "event_type": event.event_type.value,
                "agent_name": event.agent_name,
                "message": event.message,
                "payload": event.payload,
                "timestamp": event.timestamp.isoformat(),
            }
            yield {"data": json.dumps(data)}

    return EventSourceResponse(event_generator())
