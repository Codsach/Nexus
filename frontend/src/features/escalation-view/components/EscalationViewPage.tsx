import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Clock, User, Server, CheckCircle2, ArrowRight, FileText, Sparkles, ShieldAlert } from 'lucide-react'
import { getEscalatedTickets, getHandoffPacket } from '../../../lib/api'
import type { EscalationPacket, TicketListItem } from '../../../types'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'

const URGENCY_BADGE: Record<string, 'emerald' | 'amber' | 'rose' | 'slate'> = {
  low: 'emerald',
  medium: 'amber',
  high: 'amber',
  critical: 'rose',
}

const SENTIMENT_EMOJI: Record<string, string> = {
  positive: '😊', neutral: '😐', negative: '😞', very_negative: '😡',
}

function PacketView({ packet }: { packet: EscalationPacket }) {
  return (
    <div className="space-y-4 max-w-4xl mx-auto animate-fade-in pb-8">
      {/* Primary Summary Card */}
      <Card className="border-amber-200 bg-amber-50/40">
        <CardHeader className="py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
                <CardTitle className="text-base font-bold text-slate-900">
                  AI Escalation Handoff Packet
                </CardTitle>
              </div>
              <p className="text-xs text-slate-500 mt-1 font-mono">
                Ref: #{packet.ticket_id.slice(0, 8)} · Customer ID: {packet.customer_id}
              </p>
            </div>
            <Badge variant={URGENCY_BADGE[packet.priority] || 'amber'} className="text-xs uppercase px-2.5 py-0.5">
              {packet.priority} Priority
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-sm font-medium text-slate-800 leading-relaxed bg-white p-3 rounded-lg border border-amber-200/80 shadow-xs">
            {packet.issue_summary}
          </p>
        </CardContent>
      </Card>

      {/* Escalation Justification */}
      <Card className="border-slate-200 bg-white">
        <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
          <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Escalation Trigger Justification
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-amber-800 bg-amber-50/80 border border-amber-200/60 p-3 rounded-md">
            {packet.justification}
          </p>
        </CardContent>
      </Card>

      {/* Systems Investigated & Findings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Systems Checked */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
            <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Systems Checked by Agents
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-2">
              {packet.systems_checked.map((s) => (
                <div key={s} className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800 font-medium">
                  <Server size={13} className="text-emerald-600" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Sentiment Trend */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
            <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Customer Sentiment Timeline
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="flex items-center gap-2">
              {packet.customer_sentiment_trend.map((s, i) => (
                <span key={i} className="text-2xl" title={s}>{SENTIMENT_EMOJI[s] || '•'}</span>
              ))}
            </div>
            {packet.customer_sentiment_trend.length > 1 && (
              <span className="text-xs text-slate-400 font-medium">
                (Older → Newer)
              </span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Key Findings */}
      <Card className="border-slate-200 bg-white">
        <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
          <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Agent Key Findings
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <ul className="space-y-2">
            {packet.findings_summary.map((f, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-slate-800">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Actions Already Attempted */}
      {packet.actions_attempted.length > 0 && (
        <Card className="border-slate-200 bg-white">
          <CardHeader className="py-3 px-4 border-b border-slate-100 bg-slate-50/50">
            <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Autonomous Actions Attempted
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <ul className="space-y-1.5">
              {packet.actions_attempted.map((a, i) => (
                <li key={i} className="text-xs font-mono text-slate-600 bg-slate-50 p-2 rounded-md border border-slate-100 flex items-center gap-2">
                  <span className="text-emerald-600 font-bold">•</span> {a}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Recommended Next Step */}
      <Card className="border-emerald-300 bg-emerald-50/50">
        <CardHeader className="py-3 px-4 border-b border-emerald-200">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-700" />
            <CardTitle className="text-xs font-bold text-emerald-900 uppercase tracking-wider">
              Recommended Next Step for Human Agent
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-4 flex items-start gap-3">
          <ArrowRight size={18} className="text-emerald-600 shrink-0 mt-0.5" />
          <p className="text-sm font-semibold text-slate-900 leading-relaxed">
            {packet.recommended_next_step}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export default function EscalationViewPage() {
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null)

  const { data: ticketsData, isLoading } = useQuery({
    queryKey: ['escalated-tickets'],
    queryFn: getEscalatedTickets,
    refetchInterval: 5000,
  })

  const { data: packetData } = useQuery({
    queryKey: ['packet', selectedTicketId],
    queryFn: () => getHandoffPacket(selectedTicketId!),
    enabled: !!selectedTicketId,
  })

  const tickets: TicketListItem[] = ticketsData?.data || []
  const packet: EscalationPacket | null = packetData?.data || null

  return (
    <div className="flex h-[calc(100vh-64px)] mt-16 bg-slate-50 text-slate-900 font-sans">
      {/* Left queue sidebar */}
      <aside className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-600" />
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Escalation Queue
            </h2>
          </div>
          {tickets.length > 0 && (
            <Badge variant="amber" className="text-xs font-bold px-2">
              {tickets.length}
            </Badge>
          )}
        </div>

        <ScrollArea className="flex-1 p-3">
          <div className="space-y-2">
            {isLoading && (
              <div className="text-center py-8 text-slate-400 text-xs">Loading queue...</div>
            )}
            {!isLoading && tickets.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-12 px-4 border-2 border-dashed border-slate-200 rounded-lg bg-slate-50">
                <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                <div>
                  <p className="text-sm font-semibold text-slate-800">Queue Empty</p>
                  <p className="text-xs text-slate-500 mt-1">No escalated tickets requiring human intervention at this time.</p>
                </div>
              </div>
            )}
            {tickets.map((t) => {
              const isSelected = selectedTicketId === t.id
              return (
                <button
                  key={t.id}
                  id={`escalation-${t.id}`}
                  onClick={() => setSelectedTicketId(t.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all duration-150 ${
                    isSelected
                      ? 'border-emerald-500 bg-emerald-50/70 shadow-sm'
                      : 'border-slate-100 bg-white hover:border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <User size={13} className="text-slate-400" />
                      <span className="text-sm font-semibold text-slate-900">{t.customer_id}</span>
                    </div>
                    {t.urgency && (
                      <Badge variant={URGENCY_BADGE[t.urgency] || 'amber'} className="text-[10px] capitalize py-0 px-1.5">
                        {t.urgency}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 capitalize">{t.intent?.replace('_', ' ')} issue</p>
                  <div className="flex items-center gap-1 mt-2 text-[10px] text-slate-400">
                    <Clock size={11} />
                    <span>{t.created_at ? new Date(t.created_at).toLocaleTimeString() : 'N/A'}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </ScrollArea>
      </aside>

      {/* Right packet detail workspace */}
      <main className="flex-1 overflow-y-auto p-6 bg-slate-50">
        {!selectedTicketId && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-8 max-w-sm mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 border border-slate-200">
              <FileText className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Escalation Handoff Inspector</h2>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Select a ticket from the left queue to inspect the full AI handoff packet, reasoning root cause, and suggested action.
              </p>
            </div>
          </div>
        )}
        {selectedTicketId && !packet && (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-400 text-sm animate-pulse">Loading handoff packet details...</p>
          </div>
        )}
        {packet && <PacketView packet={packet} />}
      </main>
    </div>
  )
}
