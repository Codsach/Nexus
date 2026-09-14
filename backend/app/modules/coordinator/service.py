"""
Coordinator module — the entry point for all tickets.
Classifies → Routes → Dispatches agents → Generates response → Evaluates escalation.
Every step emits a trace event consumed by the live SSE panel.
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm import llm
from app.adapters.orchestration import orchestrator
from app.shared.schemas.models import (
    Ticket, Message, AgentFinding, TraceEventType, TicketStatus,
    TicketIntent, TicketUrgency, Sentiment, MessageRole,
)
from app.shared.db.database import TicketORM, AgentFindingORM, TraceEventORM
from app.shared.events import bus
from app.modules.mock_systems import store


# Registry of specialist agents
def _get_agent(name: str):
    if name == "billing":
        from app.modules.specialist_agents.billing.agent import BillingAgent
        return BillingAgent()
    elif name == "order":
        from app.modules.specialist_agents.order.agent import OrderAgent
        return OrderAgent()
    elif name == "technical":
        from app.modules.specialist_agents.technical.agent import TechnicalAgent
        return TechnicalAgent()
    elif name == "account":
        from app.modules.specialist_agents.account.agent import AccountAgent
        return AccountAgent()
    raise ValueError(f"Unknown agent: {name}")


async def create_ticket(
    customer_id: str,
    message_text: str,
    db: AsyncSession,
) -> Ticket:
    """Create ticket in DB and return the Ticket schema object."""
    ticket_id = str(uuid.uuid4())
    msg = Message(
        ticket_id=ticket_id,
        role=MessageRole.customer,
        content=message_text,
    )
    ticket = Ticket(
        id=ticket_id,
        customer_id=customer_id,
        status=TicketStatus.open,
        messages=[msg],
    )
    db_ticket = TicketORM(
        id=ticket.id,
        customer_id=ticket.customer_id,
        status=ticket.status.value,
        messages_json=json.dumps([msg.model_dump(mode="json")]),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )
    db.add(db_ticket)
    await db.commit()
    return ticket


async def process_ticket(
    ticket_id: str,
    customer_id: str,
    message_text: str,
    db: AsyncSession,
) -> dict:
    """
    Full coordinator pipeline:
    1. Emit ticket_created
    2. Classify intent/urgency/sentiment
    3. Look up CRM context
    4. Route to specialist agent(s) via orchestrator
    5. Dispatch agents (parallel if multi-domain)
    6. RAG retrieval (knowledge engine)
    7. Generate final response
    8. Evaluate escalation
    9. Emit auto_resolved or escalation_triggered
    10. Persist result
    """
    # 1. Ticket created
    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.ticket_created,
        message=f"📥 Ticket created for customer {customer_id}",
        customer_id=customer_id,
    ))

    # 2. Classify
    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.classification_complete,
        message="🧠 Classifying intent, urgency, and sentiment...",
    ))

    classification = await llm.classify(message_text, context={"customer_id": customer_id})

    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.classification_complete,
        message=(
            f"🏷️ Classification: intent={classification.intent} | "
            f"urgency={classification.urgency} | sentiment={classification.sentiment} | "
            f"confidence={classification.confidence:.0%}"
        ),
        intent=classification.intent,
        urgency=classification.urgency,
        sentiment=classification.sentiment,
        confidence=classification.confidence,
        reasoning=classification.reasoning,
    ))

    # Update ticket in DB
    await db.execute(
        update(TicketORM)
        .where(TicketORM.id == ticket_id)
        .values(
            intent=classification.intent,
            urgency=classification.urgency,
            sentiment=classification.sentiment,
            status=TicketStatus.investigating.value,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    # 3. CRM context
    crm = store.get_crm(customer_id)
    customer_tier = crm.tier if crm else "Standard"
    customer_name = crm.name if crm else "Customer"

    # 4. Route
    route = await orchestrator.route(
        intent=classification.intent,
        urgency=classification.urgency,
        confidence=classification.confidence,
        customer_tier=customer_tier,
    )

    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.routing_decision,
        message=f"🔀 Routing: agents={route.agents} | parallel={route.parallel} — {route.reasoning}",
        agents=route.agents,
        parallel=route.parallel,
        reasoning=route.reasoning,
    ))

    # 5. Dispatch agents
    findings: list[AgentFinding] = []

    if route.parallel and len(route.agents) > 1:
        # Parallel dispatch via orchestrator
        tasks = [
            _run_agent(name, ticket_id, customer_id, message_text)
            for name in route.agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        findings = [r for r in results if isinstance(r, AgentFinding)]
    else:
        for agent_name in route.agents:
            finding = await _run_agent(agent_name, ticket_id, customer_id, message_text)
            if finding:
                findings.append(finding)

    # Persist findings
    for f in findings:
        db.add(AgentFindingORM(
            id=f.id,
            ticket_id=f.ticket_id,
            agent_name=f.agent_name,
            summary=f.summary,
            evidence_json=json.dumps(f.evidence),
            confidence=f.confidence,
            actions_available_json=json.dumps(f.actions_available),
            root_cause=f.root_cause,
            raw_data_json=json.dumps(f.raw_data),
        ))
    await db.commit()

    # 6. RAG retrieval
    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.rag_retrieved,
        message="📚 Retrieving relevant KB articles and past ticket context...",
    ))

    rag_context = await _retrieve_rag_context(message_text, ticket_id)

    # 7. Generate response
    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.response_generating,
        message="✍️ Generating grounded customer response...",
    ))

    # Build context for response generation
    primary_finding = findings[0] if findings else None
    domain = classification.intent if classification.intent != "multi" else (
        findings[0].agent_name if findings else "billing"
    )
    sub_type = primary_finding.raw_data.get("sub_type", "default") if primary_finding else "default"

    response_ctx = {
        "task_type": "customer_response",
        "domain": domain,
        "sub_type": sub_type,
        "customer": {"name": customer_name, "tier": customer_tier},
        "findings": primary_finding.raw_data if primary_finding else {},
        "citation_ids": rag_context.get("citation_ids", []),
    }
    if classification.intent == "multi" and len(findings) >= 2:
        response_ctx["domain"] = "multi"
        response_ctx["findings"]["billing_summary"] = findings[0].evidence[0] if findings[0].evidence else ""
        response_ctx["findings"]["order_summary"] = findings[1].evidence[0] if len(findings) > 1 and findings[1].evidence else ""
        response_ctx["findings"]["resolution"] = "processing both billing and order resolutions simultaneously"

    response_result = await llm.complete(
        prompt=f"Generate a customer support response for: {message_text}",
        context=response_ctx,
    )

    # 8. Escalation evaluation
    from app.modules.escalation.scorer import evaluate_escalation
    escalation_result = await evaluate_escalation(
        ticket_id=ticket_id,
        customer_id=customer_id,
        findings=findings,
        urgency=classification.urgency,
        customer_tier=customer_tier,
        db=db,
    )

    # 9. Resolve / escalate
    final_status = TicketStatus.escalated if escalation_result["should_escalate"] else TicketStatus.resolved
    resolved_at = datetime.now(timezone.utc)
    resolution_seconds = (resolved_at - datetime.now(timezone.utc).replace(microsecond=0)).total_seconds()

    # Build final response message
    final_message_content = response_result.content
    if escalation_result["should_escalate"]:
        final_message_content = (
            f"I understand this situation requires immediate attention. "
            f"I'm escalating your case to our senior support team who will contact you shortly. "
            f"I've prepared a complete summary so you won't need to repeat yourself. "
            f"Escalation reason: {escalation_result['justification']}"
        )

    # Persist assistant response message
    final_msg = Message(
        ticket_id=ticket_id,
        role=MessageRole.assistant,
        content=final_message_content,
    )

    # Fetch current messages, append
    result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
    db_ticket = result.scalar_one_or_none()
    if db_ticket:
        existing_msgs = json.loads(db_ticket.messages_json or "[]")
        existing_msgs.append(final_msg.model_dump(mode="json"))
        await db.execute(
            update(TicketORM)
            .where(TicketORM.id == ticket_id)
            .values(
                status=final_status.value,
                messages_json=json.dumps(existing_msgs),
                resolved_at=resolved_at,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    # 10. Emit completion event
    if escalation_result["should_escalate"]:
        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.escalation_triggered,
            message=f"🚨 Escalated to human queue — {escalation_result['justification']}",
            justification=escalation_result["justification"],
        ))
    else:
        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.auto_resolved,
            message=f"✅ Auto-resolved — combined confidence: {escalation_result['combined_confidence']:.0%}",
            confidence=escalation_result["combined_confidence"],
        ))

    # Signal end of trace stream
    await asyncio.sleep(0.1)
    await bus.close_stream(ticket_id)

    return {
        "ticket_id": ticket_id,
        "status": final_status.value,
        "response": final_message_content,
        "intent": classification.intent,
        "urgency": classification.urgency,
        "sentiment": classification.sentiment,
        "agents_invoked": [f.agent_name for f in findings],
        "escalated": escalation_result["should_escalate"],
        "escalation_packet_id": escalation_result.get("packet_id"),
        "citations": rag_context.get("citations", []),
    }


async def _run_agent(agent_name: str, ticket_id: str, customer_id: str, message: str) -> AgentFinding | None:
    try:
        agent = _get_agent(agent_name)
        return await agent.investigate(ticket_id, customer_id, message)
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"Agent {agent_name} failed for ticket {ticket_id}: {e}")
        return None


async def _retrieve_rag_context(query: str, ticket_id: str) -> dict:
    """Retrieve knowledge base context. Falls back gracefully if RAG unavailable."""
    try:
        from app.modules.knowledge_engine.retriever import retrieve
        chunks = await retrieve(query, top_k=3)
        citation_ids = [c.id for c in chunks]
        citations = [{"source": c.source, "excerpt": c.content[:120]} for c in chunks]
        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.rag_retrieved,
            message=f"📖 Retrieved {len(chunks)} KB articles: {', '.join(c.source for c in chunks[:2])}",
            chunk_count=len(chunks),
        ))
        return {"citation_ids": citation_ids, "citations": citations}
    except Exception:
        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.rag_retrieved,
            message="📖 KB retrieval skipped (index not available)",
        ))
        return {"citation_ids": [], "citations": []}
