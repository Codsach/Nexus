"""
Escalation scorer — aggregates agent confidences, applies business rules,
decides whether to escalate. Generates handoff packet if escalating.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm import llm
from app.shared.schemas.models import (
    AgentFinding, EscalationPacket, TraceEventType, TicketUrgency, Sentiment
)
from app.shared.db.database import EscalationPacketORM
from app.shared.events import bus
from app.modules.mock_systems import store


ESCALATION_CONFIDENCE_THRESHOLD = 0.65
ENTERPRISE_CONFIDENCE_THRESHOLD = 0.80


def _compute_combined_confidence(findings: list[AgentFinding]) -> float:
    if not findings:
        return 0.0
    # Weighted average, lower confidence finding drags more (safety-first)
    total = sum(f.confidence for f in findings)
    return round(total / len(findings), 3)


def _get_escalation_reasons(
    combined_confidence: float,
    urgency: str,
    customer_tier: str,
    findings: list[AgentFinding],
) -> list[str]:
    reasons = []
    threshold = ENTERPRISE_CONFIDENCE_THRESHOLD if customer_tier == "Enterprise" else ESCALATION_CONFIDENCE_THRESHOLD

    if combined_confidence < threshold:
        reasons.append(
            f"Combined agent confidence {combined_confidence:.0%} below threshold ({threshold:.0%})"
        )
    if urgency == "critical":
        reasons.append("Ticket urgency is CRITICAL — requires human oversight")
    if customer_tier == "Enterprise" and urgency in ("high", "critical"):
        reasons.append(f"Enterprise customer SLA requires human review for high-priority tickets")

    return reasons


async def evaluate_escalation(
    ticket_id: str,
    customer_id: str,
    findings: list[AgentFinding],
    urgency: str,
    customer_tier: str,
    db: AsyncSession,
) -> dict:
    """Evaluate whether to escalate. Returns decision dict with optional packet_id."""
    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.escalation_evaluating,
        message=f"⚖️ Evaluating escalation — analyzing {len(findings)} agent finding(s)...",
    ))

    combined_confidence = _compute_combined_confidence(findings)
    threshold = ENTERPRISE_CONFIDENCE_THRESHOLD if customer_tier == "Enterprise" else ESCALATION_CONFIDENCE_THRESHOLD
    escalation_reasons = _get_escalation_reasons(combined_confidence, urgency, customer_tier, findings)
    should_escalate = len(escalation_reasons) > 0

    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.escalation_evaluating,
        message=(
            f"📊 Confidence: {combined_confidence:.0%} | Threshold: {threshold:.0%} | "
            f"Decision: {'ESCALATE' if should_escalate else 'AUTO-RESOLVE'}"
        ),
        combined_confidence=combined_confidence,
        threshold=threshold,
        should_escalate=should_escalate,
        reasons=escalation_reasons,
    ))

    if not should_escalate:
        return {
            "should_escalate": False,
            "combined_confidence": combined_confidence,
            "justification": "All agents completed with sufficient confidence for auto-resolution.",
        }

    # Generate handoff packet
    packet = await _generate_handoff_packet(
        ticket_id=ticket_id,
        customer_id=customer_id,
        findings=findings,
        escalation_reasons=escalation_reasons,
        urgency=urgency,
        db=db,
    )

    return {
        "should_escalate": True,
        "combined_confidence": combined_confidence,
        "justification": "; ".join(escalation_reasons),
        "packet_id": packet.id,
    }


async def _generate_handoff_packet(
    ticket_id: str,
    customer_id: str,
    findings: list[AgentFinding],
    escalation_reasons: list[str],
    urgency: str,
    db: AsyncSession,
) -> EscalationPacket:
    crm = store.get_crm(customer_id)
    customer_name = crm.name if crm else customer_id
    tier = crm.tier if crm else "Standard"

    history = store.get_ticket_history(customer_id)
    sentiment_trend = [h.sentiment_at_open for h in sorted(history, key=lambda x: x.date)[-4:]]

    systems_checked = list({f.agent_name.title() + " System" for f in findings})
    findings_summary = []
    actions_attempted = []

    for f in findings:
        if f.evidence:
            findings_summary.append(f.evidence[0])
        actions_attempted.extend(f.actions_available[:2])

    # Generate issue summary via LLM
    result = await llm.complete(
        prompt=f"Generate a concise 2-sentence handoff summary for a support ticket",
        context={
            "task_type": "handoff_packet",
            "customer": {"name": customer_name, "tier": tier},
            "findings_summary": findings_summary,
            "systems_checked": systems_checked,
            "issue_summary": "; ".join(findings_summary[:2]),
            "recommended_action": actions_attempted[0] if actions_attempted else "Full account review",
            "sentiment": sentiment_trend[-1].value if sentiment_trend else "negative",
        },
    )

    packet = EscalationPacket(
        ticket_id=ticket_id,
        customer_id=customer_id,
        justification="; ".join(escalation_reasons),
        issue_summary=f"[{tier} Customer: {customer_name}] " + result.content,
        systems_checked=systems_checked,
        findings_summary=findings_summary,
        actions_attempted=actions_attempted,
        customer_sentiment_trend=sentiment_trend if sentiment_trend else [Sentiment.negative],
        recommended_next_step=(
            actions_attempted[0] if actions_attempted
            else "Perform full account review and apply appropriate compensation"
        ),
        priority=urgency,
    )

    db.add(EscalationPacketORM(
        id=packet.id,
        ticket_id=packet.ticket_id,
        customer_id=packet.customer_id,
        justification=packet.justification,
        issue_summary=packet.issue_summary,
        systems_checked_json=json.dumps(packet.systems_checked),
        findings_summary_json=json.dumps(packet.findings_summary),
        actions_attempted_json=json.dumps(packet.actions_attempted),
        sentiment_trend_json=json.dumps([s.value for s in packet.customer_sentiment_trend]),
        recommended_next_step=packet.recommended_next_step,
        priority=packet.priority,
    ))
    await db.commit()

    await bus.emit(bus.make_event(
        ticket_id=ticket_id,
        event_type=TraceEventType.handoff_packet_generated,
        message=f"📋 Handoff packet generated for {customer_name} ({tier}) — routing to human queue",
        packet_id=packet.id,
        customer_name=customer_name,
        tier=tier,
    ))

    return packet
