"""
Shared Pydantic schemas — every cross-module entity is defined exactly once here.
Modules import these; they never redefine another module's entity shape.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TicketStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    escalated = "escalated"


class TicketIntent(str, Enum):
    billing = "billing"
    order = "order"
    technical = "technical"
    account = "account"
    multi = "multi"
    unknown = "unknown"


class TicketUrgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    very_negative = "very_negative"


class MessageRole(str, Enum):
    customer = "customer"
    assistant = "assistant"
    system = "system"


class TraceEventType(str, Enum):
    ticket_created = "ticket_created"
    classification_complete = "classification_complete"
    routing_decision = "routing_decision"
    agent_started = "agent_started"
    agent_finished = "agent_finished"
    rag_retrieved = "rag_retrieved"
    response_generating = "response_generating"
    response_complete = "response_complete"
    escalation_evaluating = "escalation_evaluating"
    escalation_triggered = "escalation_triggered"
    auto_resolved = "auto_resolved"
    handoff_packet_generated = "handoff_packet_generated"


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    status: TicketStatus = TicketStatus.open
    intent: Optional[TicketIntent] = None
    urgency: Optional[TicketUrgency] = None
    sentiment: Optional[Sentiment] = None
    messages: list[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_time_seconds: Optional[float] = None


class AgentFinding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    agent_name: str  # "billing" | "order" | "technical" | "account"
    summary: str
    evidence: list[str]  # bullet-point evidence items
    confidence: float = Field(ge=0.0, le=1.0)
    actions_available: list[str] = []
    root_cause: Optional[str] = None
    raw_data: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TraceEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    event_type: TraceEventType
    agent_name: Optional[str] = None
    payload: dict[str, Any] = {}
    message: str  # human-readable description shown in UI
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EscalationPacket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    customer_id: str
    justification: str  # why escalated
    issue_summary: str  # 2-3 sentence summary for human agent
    systems_checked: list[str]  # which mock systems were queried
    findings_summary: list[str]  # key points from agent findings
    actions_attempted: list[str]
    customer_sentiment_trend: list[Sentiment]  # most recent last
    recommended_next_step: str
    priority: TicketUrgency
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str  # document name / ticket ID
    source_type: str  # "faq" | "kb_article" | "resolved_ticket" | "policy"
    content: str
    metadata: dict[str, Any] = {}


class Citation(BaseModel):
    chunk_id: str
    source: str
    source_type: str
    relevance_score: float
    excerpt: str  # short snippet shown in UI


class AnalyticsSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    period: str  # "2024-09" etc.
    cluster_label: str
    ticket_count: int
    trend_direction: str  # "rising" | "falling" | "stable"
    trend_narrative: str  # LLM-generated plain-language explanation
    example_tickets: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Mock system records
# ---------------------------------------------------------------------------

class CRMRecord(BaseModel):
    customer_id: str
    name: str
    email: str
    tier: str  # "Standard" | "Premium" | "Enterprise"
    account_status: str  # "active" | "suspended" | "at_risk"
    join_date: str
    total_spend_usd: float
    contact_history: list[dict[str, Any]] = []
    notes: str = ""


class BillingTransaction(BaseModel):
    transaction_id: str
    date: str
    amount_usd: float
    description: str
    status: str  # "completed" | "refunded" | "disputed" | "pending"
    reference: str = ""


class BillingRecord(BaseModel):
    customer_id: str
    subscription_plan: str
    subscription_status: str  # "active" | "cancelled" | "past_due"
    next_billing_date: str
    payment_method: str
    transactions: list[BillingTransaction] = []
    total_refunds_usd: float = 0.0
    disputed_charges: list[str] = []


class ShippingEvent(BaseModel):
    timestamp: str
    location: str
    status: str
    description: str


class OrderRecord(BaseModel):
    order_id: str
    customer_id: str
    product_name: str
    sku: str
    quantity: int
    unit_price_usd: float
    total_usd: float
    order_date: str
    expected_delivery: str
    actual_delivery: Optional[str] = None
    status: str  # "processing" | "shipped" | "delivered" | "lost" | "return_initiated"
    tracking_number: str
    shipping_events: list[ShippingEvent] = []
    fulfillment_notes: str = ""


class TicketHistoryRecord(BaseModel):
    record_id: str
    customer_id: str
    ticket_id: str
    date: str
    category: str
    issue_summary: str
    resolution: str
    resolved_by: str  # "auto" | "human"
    sentiment_at_open: Sentiment
    sentiment_at_close: Sentiment
    resolution_time_hours: float
