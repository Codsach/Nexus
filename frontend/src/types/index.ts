export type Role = 'customer' | 'agent' | 'manager'

export type TicketStatus = 'open' | 'investigating' | 'resolved' | 'escalated'
export type TicketIntent = 'billing' | 'order' | 'technical' | 'account' | 'multi' | 'unknown'
export type Urgency = 'low' | 'medium' | 'high' | 'critical'
export type Sentiment = 'positive' | 'neutral' | 'negative' | 'very_negative'
export type TraceEventType =
  | 'ticket_created'
  | 'classification_complete'
  | 'routing_decision'
  | 'agent_started'
  | 'agent_finished'
  | 'rag_retrieved'
  | 'response_generating'
  | 'response_complete'
  | 'escalation_evaluating'
  | 'escalation_triggered'
  | 'auto_resolved'
  | 'handoff_packet_generated'

export interface Message {
  id: string
  ticket_id: string
  role: 'customer' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export interface AgentFinding {
  agent: string
  summary: string
  evidence: string[]
  confidence: number
  actions: string[]
  root_cause?: string
}

export interface Ticket {
  id: string
  customer_id: string
  status: TicketStatus
  intent?: TicketIntent
  urgency?: Urgency
  sentiment?: Sentiment
  messages: Message[]
  created_at: string
  updated_at: string
  findings: AgentFinding[]
}

export interface TicketListItem {
  id: string
  customer_id: string
  status: TicketStatus
  intent?: TicketIntent
  urgency?: Urgency
  sentiment?: Sentiment
  created_at: string
}

export interface TraceEvent {
  id: string
  ticket_id: string
  event_type: TraceEventType
  agent_name?: string
  message: string
  payload: Record<string, unknown>
  timestamp: string
}

export interface EscalationPacket {
  id: string
  ticket_id: string
  customer_id: string
  justification: string
  issue_summary: string
  systems_checked: string[]
  findings_summary: string[]
  actions_attempted: string[]
  customer_sentiment_trend: Sentiment[]
  recommended_next_step: string
  priority: Urgency
  created_at: string
}

export interface AnalyticsOverview {
  total_tickets: number
  live_tickets: number
  resolved: number
  escalated: number
  open: number
  resolution_rate_pct: number
  escalation_rate_pct: number
  avg_resolution_time_minutes: number
  intent_breakdown: Record<string, number>
  urgency_breakdown: Record<string, number>
  tickets_by_month: Record<string, number>
}

export interface ClusterItem {
  cluster_label: string
  category: string
  ticket_count: number
  trend_direction: 'rising' | 'falling' | 'stable'
  trend_narrative: string
  example_issues: string[]
}

export interface ChurnRiskItem {
  customer_id: string
  customer_name: string
  tier: string
  account_status: string
  risk_score: number
  risk_level: 'medium' | 'high' | 'critical'
  ticket_count: number
  negative_tickets: number
  unresolved_tickets: number
  total_spend_usd: number
  sentiment_trend: Sentiment[]
  notes: string
}
