import { useRef, useEffect } from 'react'
import type { TraceEvent, TraceEventType } from '../../../types'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Brain, CheckCircle2, Clock, Sparkles, AlertCircle, ArrowRightLeft, Search, FileText } from 'lucide-react'

interface Props {
  events: TraceEvent[]
  connected: boolean
  done: boolean
}

const EVENT_CONFIG: Record<TraceEventType, { icon: React.ReactNode; color: string; badgeVariant: 'emerald' | 'amber' | 'teal' | 'slate' | 'rose' }> = {
  ticket_created:           { icon: <FileText className="w-3.5 h-3.5 text-emerald-600" />,   color: 'text-slate-900', badgeVariant: 'emerald' },
  classification_complete:  { icon: <Sparkles className="w-3.5 h-3.5 text-teal-600" />,     color: 'text-slate-900', badgeVariant: 'teal' },
  routing_decision:         { icon: <ArrowRightLeft className="w-3.5 h-3.5 text-teal-600" />, color: 'text-slate-900', badgeVariant: 'teal' },
  agent_started:            { icon: <Search className="w-3.5 h-3.5 text-amber-600" />,      color: 'text-slate-900', badgeVariant: 'amber' },
  agent_finished:           { icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />, color: 'text-slate-900', badgeVariant: 'emerald' },
  rag_retrieved:            { icon: <Search className="w-3.5 h-3.5 text-teal-600" />,       color: 'text-slate-900', badgeVariant: 'teal' },
  response_generating:      { icon: <Sparkles className="w-3.5 h-3.5 text-emerald-600" />, color: 'text-slate-900', badgeVariant: 'emerald' },
  response_complete:        { icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />, color: 'text-slate-900', badgeVariant: 'emerald' },
  escalation_evaluating:    { icon: <AlertCircle className="w-3.5 h-3.5 text-amber-600" />,  color: 'text-amber-900', badgeVariant: 'amber' },
  escalation_triggered:     { icon: <AlertCircle className="w-3.5 h-3.5 text-rose-600" />,   color: 'text-rose-900', badgeVariant: 'rose' },
  auto_resolved:            { icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />, color: 'text-emerald-900', badgeVariant: 'emerald' },
  handoff_packet_generated: { icon: <FileText className="w-3.5 h-3.5 text-amber-600" />,    color: 'text-amber-900', badgeVariant: 'amber' },
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function ReasoningTracePanel({ events, connected, done }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  const isEmpty = events.length === 0

  return (
    <Card className="flex flex-col h-full border-slate-200 bg-slate-50/50 shadow-none rounded-xl overflow-hidden">
      {/* Panel Header */}
      <CardHeader className="py-3 px-4 border-b border-slate-200 bg-white flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-emerald-100 flex items-center justify-center">
            <Brain className="w-3.5 h-3.5 text-emerald-700" />
          </div>
          <CardTitle className="text-sm font-semibold text-slate-800">
            AI Reasoning Trace
          </CardTitle>
        </div>
        <Badge
          variant={done ? 'emerald' : connected ? 'teal' : 'slate'}
          className="text-[11px] font-medium px-2 py-0.5"
        >
          {done ? 'Complete' : connected ? 'Live Stream' : events.length > 0 ? 'Idle' : 'Waiting'}
        </Badge>
      </CardHeader>

      {/* Events Feed */}
      <CardContent className="flex-1 p-3 overflow-hidden">
        <ScrollArea className="h-full pr-1">
          {isEmpty && (
            <div className="flex flex-col items-center justify-center min-h-[300px] h-full gap-3 text-center p-6 border-2 border-dashed border-slate-200 rounded-lg bg-white/60">
              <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                <Brain className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">
                  Ready for Reasoning Input
                </p>
                <p className="text-xs text-slate-400 mt-1 max-w-[220px]">
                  Submit a ticket to observe live LLM agent orchestration and decision steps.
                </p>
              </div>
            </div>
          )}

          <div className="space-y-2">
            {events.map((event, i) => {
              const cfg = EVENT_CONFIG[event.event_type] ?? { icon: <Clock className="w-3.5 h-3.5 text-slate-400" />, color: 'text-slate-800', badgeVariant: 'slate' }
              return (
                <div
                  key={event.id || i}
                  className="p-2.5 rounded-lg border border-slate-200 bg-white shadow-sm transition-all hover:border-slate-300"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded-md bg-slate-50 border border-slate-100 shrink-0">
                        {cfg.icon}
                      </div>
                      <span className={`text-xs font-medium ${cfg.color}`}>
                        {event.message}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono shrink-0">
                      {formatTime(event.timestamp)}
                    </span>
                  </div>

                  {event.agent_name && (
                    <div className="mt-1 ml-7 flex items-center gap-1.5">
                      <span className="text-[10px] text-slate-400">Agent:</span>
                      <Badge variant="slate" className="text-[10px] py-0 px-1.5 font-medium">
                        {event.agent_name}
                      </Badge>
                    </div>
                  )}

                  {event.payload && Object.keys(event.payload).length > 0 && (
                    <div className="mt-2 ml-7 p-2 rounded-md bg-slate-50 border border-slate-100 text-[11px] font-mono text-slate-600 space-y-0.5">
                      {Object.entries(event.payload)
                        .filter(([k]) => ['confidence', 'intent', 'urgency', 'sentiment', 'agents', 'reasoning', 'justification'].includes(k))
                        .slice(0, 3)
                        .map(([k, v]) => (
                          <div key={k} className="truncate flex items-center gap-1">
                            <span className="text-emerald-700 font-semibold">{k}:</span>
                            <span className="text-slate-700">{JSON.stringify(v)}</span>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              )
            })}

            {/* Live Streaming Loader */}
            {connected && !done && (
              <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center gap-2.5 animate-pulse">
                <Sparkles className="w-4 h-4 text-emerald-600 animate-spin" />
                <span className="text-xs font-medium text-emerald-800">
                  LLM Agents synthesizing solution...
                </span>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </CardContent>

      {/* Footer Summary */}
      {events.length > 0 && (
        <div className="py-2 px-4 border-t border-slate-200 bg-white flex items-center justify-between text-xs text-slate-500">
          <span>{events.length} reasoning steps</span>
          {done && (
            <span className="text-emerald-600 font-semibold flex items-center gap-1">
              <CheckCircle2 size={12} /> Execution complete
            </span>
          )}
        </div>
      )}
    </Card>
  )
}
