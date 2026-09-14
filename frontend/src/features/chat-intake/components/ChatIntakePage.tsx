import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Send, RefreshCw, Sparkles, MessageSquare, User, Bot, AlertCircle, CheckCircle2 } from 'lucide-react'
import { submitTicket, getTicket } from '../../../lib/api'
import { useAppStore } from '../../../store/appStore'
import { useSSETrace } from '../../../hooks/useSSETrace'
import ReasoningTracePanel from '../../reasoning-trace/components/ReasoningTracePanel'
import type { Message } from '../../../types'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { ScrollArea } from '@/components/ui/scroll-area'

const DEMO_CUSTOMERS = [
  { id: 'C001', name: 'Sarah Mitchell', tier: 'Premium', scenario: 'Billing Dispute' },
  { id: 'C003', name: 'Priya Sharma', tier: 'Standard', scenario: 'Lost Package' },
  { id: 'C004', name: 'James Kowalski', tier: 'Standard', scenario: 'Delayed Order (Churn Risk)' },
  { id: 'C005', name: 'Elena Volkov', tier: 'Premium', scenario: 'Duplicate Charge (Critical Churn)' },
  { id: 'C007', name: 'Aisha Nakamura', tier: 'Enterprise', scenario: 'Account Permissions' },
  { id: 'C008', name: 'Roberto Ferrara', tier: 'Standard', scenario: 'Account Suspended' },
]

const DEMO_MESSAGES: Record<string, string> = {
  C001: "I was charged twice this month! I see two charges of $49.99 on September 15th. This is unacceptable, please refund the duplicate charge immediately.",
  C003: "My order was supposed to arrive on September 8th but I still haven't received it. The tracking says delivered but nothing is here. Where is my package?",
  C004: "My package has been stuck at the Memphis hub for over a week now. This is the third problem I've had with your service this month. I'm very frustrated.",
  C005: "I am furious. I've been charged TWICE for my Premium subscription this month, AND my last order had the wrong item. This is absolutely unacceptable. I want to speak to a manager.",
  C007: "Five of my team members cannot access their accounts since we made some permission changes in the admin panel. This is blocking our entire workflow. We need this fixed urgently.",
  C008: "My account says suspended and I can't access anything. I'm sure my card is valid. What's going on?",
}

const URGENCY_BADGE: Record<string, 'emerald' | 'amber' | 'rose' | 'slate'> = {
  low: 'emerald',
  medium: 'amber',
  high: 'amber',
  critical: 'rose',
}

const STATUS_BADGE: Record<string, 'emerald' | 'amber' | 'teal' | 'slate'> = {
  open: 'slate',
  investigating: 'teal',
  resolved: 'emerald',
  escalated: 'amber',
}

export default function ChatIntakePage() {
  const [selectedCustomer, setSelectedCustomer] = useState(DEMO_CUSTOMERS[0])
  const [inputMessage, setInputMessage] = useState(DEMO_MESSAGES.C001)
  const [ticketId, setTicketId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [ticketStatus, setTicketStatus] = useState<string | null>(null)
  const [ticketMeta, setTicketMeta] = useState<{intent?: string, urgency?: string, sentiment?: string} | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { setActiveTicketId } = useAppStore()

  const { events, connected, done } = useSSETrace(ticketId)

  const submitMutation = useMutation({
    mutationFn: ({ customerId, message }: { customerId: string; message: string }) =>
      submitTicket(customerId, message),
    onSuccess: (res) => {
      const id = res.data.ticket_id
      setTicketId(id)
      setActiveTicketId(id)
      setTicketStatus('investigating')
      setMessages([{
        id: 'user-' + id,
        ticket_id: id,
        role: 'customer',
        content: inputMessage,
        timestamp: new Date().toISOString(),
      }])
      setInputMessage('')
    },
  })

  // Poll ticket state
  const { data: ticketData, refetch } = useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => getTicket(ticketId!),
    enabled: Boolean(ticketId),
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status
      if (status === 'resolved' || status === 'escalated') {
        return false
      }
      return 1500
    },
  })

  useEffect(() => {
    if (done && ticketId) {
      setTimeout(() => refetch(), 300)
    }
  }, [done, ticketId])

  useEffect(() => {
    if (ticketData?.data) {
      const t = ticketData.data
      setMessages(t.messages || [])
      setTicketStatus(t.status)
      setTicketMeta({ intent: t.intent, urgency: t.urgency, sentiment: t.sentiment })
    }
  }, [ticketData])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleCustomerSelect = (c: typeof DEMO_CUSTOMERS[0]) => {
    setSelectedCustomer(c)
    setInputMessage(DEMO_MESSAGES[c.id] || '')
    setTicketId(null)
    setMessages([])
    setTicketStatus(null)
    setTicketMeta(null)
  }

  const handleSubmit = () => {
    if (!inputMessage.trim() || submitMutation.isPending) return
    submitMutation.mutate({
      customerId: selectedCustomer.id,
      message: inputMessage.trim(),
    })
  }

  return (
    <div className="flex h-[calc(100vh-64px)] mt-16 bg-slate-50 text-slate-900 font-sans">
      {/* Left sidebar — Demo customer presets */}
      <aside className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Demo Customers Preset
          </h2>
          <div className="space-y-1.5">
            {DEMO_CUSTOMERS.map((c) => {
              const isSelected = selectedCustomer.id === c.id
              return (
                <button
                  key={c.id}
                  id={`customer-${c.id}`}
                  onClick={() => handleCustomerSelect(c)}
                  className={`w-full text-left p-3 rounded-lg border transition-all duration-150 ${
                    isSelected
                      ? 'border-emerald-500 bg-emerald-50/70 shadow-sm'
                      : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm text-slate-900">{c.name}</span>
                    <Badge
                      variant={c.tier === 'Enterprise' ? 'amber' : c.tier === 'Premium' ? 'emerald' : 'slate'}
                      className="text-[10px] px-1.5 py-0 font-medium"
                    >
                      {c.tier}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 truncate">{c.scenario}</p>
                </button>
              )
            })}
          </div>
        </div>

        {/* Active Ticket Metadata Analysis */}
        {ticketMeta && (
          <div className="p-4 flex-1 bg-slate-50/60 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              AI Ticket Analysis
            </h3>
            <Card className="p-3 space-y-2.5 bg-white border-slate-200">
              {ticketMeta.intent && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Intent</span>
                  <span className="font-semibold text-slate-800 capitalize">{ticketMeta.intent}</span>
                </div>
              )}
              {ticketMeta.urgency && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Urgency</span>
                  <Badge variant={URGENCY_BADGE[ticketMeta.urgency] || 'slate'} className="capitalize text-[10px]">
                    {ticketMeta.urgency}
                  </Badge>
                </div>
              )}
              {ticketMeta.sentiment && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Sentiment</span>
                  <span className="font-semibold text-slate-800 capitalize">{ticketMeta.sentiment.replace('_', ' ')}</span>
                </div>
              )}
              {ticketStatus && (
                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
                  <span className="text-slate-500 font-medium">Status</span>
                  <Badge variant={STATUS_BADGE[ticketStatus] || 'slate'} className="capitalize text-[10px]">
                    {ticketStatus}
                  </Badge>
                </div>
              )}
            </Card>
          </div>
        )}
      </aside>

      {/* Main LLM Chat Interface Workspace */}
      <main className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Workspace Top Header */}
        <div className="px-6 py-3.5 border-b border-slate-200 flex items-center justify-between bg-white shadow-xs">
          <div className="flex items-center gap-3">
            <Avatar className="h-9 w-9 border-slate-200 bg-emerald-100">
              <AvatarFallback className="text-emerald-800 font-semibold">
                {selectedCustomer.name.split(' ').map(n => n[0]).join('')}
              </AvatarFallback>
            </Avatar>
            <div>
              <h1 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                {selectedCustomer.name}
                <Badge variant="outline" className="text-[10px] font-normal text-slate-500">
                  ID: {selectedCustomer.id}
                </Badge>
              </h1>
              <p className="text-xs text-slate-500">{selectedCustomer.scenario}</p>
            </div>
          </div>

          {ticketId && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">
                Ref: #{ticketId.slice(0, 8)}
              </span>
              {ticketStatus && (
                <Badge variant={STATUS_BADGE[ticketStatus] || 'slate'} className="capitalize text-xs">
                  {ticketStatus}
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Chat Feed Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          <ScrollArea className="h-full pr-2">
            {messages.length === 0 && !submitMutation.isPending && (
              <div className="flex flex-col items-center justify-center min-h-[420px] h-full gap-4 text-center p-8 max-w-md mx-auto">
                <div className="w-14 h-14 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700 shadow-sm border border-emerald-200">
                  <Bot className="w-7 h-7" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Nexus AI Support Studio</h2>
                  <p className="text-slate-500 text-xs mt-1 leading-relaxed">
                    Submit your ticket to initiate multi-agent reasoning, RAG retrieval, and real-time resolution.
                  </p>
                </div>
                <div className="w-full space-y-2 mt-2">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Quick Preset Scenarios</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {DEMO_CUSTOMERS.slice(0, 4).map((c) => (
                      <Button
                        key={c.id}
                        variant="outline"
                        size="sm"
                        onClick={() => handleCustomerSelect(c)}
                        className="text-xs h-8 text-slate-700 border-slate-200 hover:border-emerald-500 hover:bg-emerald-50/50"
                      >
                        {c.scenario}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-4 max-w-3xl mx-auto">
              {messages.map((msg, i) => {
                const isCustomer = msg.role === 'customer'
                return (
                  <div
                    key={msg.id || i}
                    className={`flex items-start gap-3 ${isCustomer ? 'flex-row-reverse' : 'flex-row'} animate-fade-in`}
                  >
                    <Avatar className={`h-8 w-8 shrink-0 ${isCustomer ? 'bg-slate-200 text-slate-700' : 'bg-emerald-600 text-white'}`}>
                      <AvatarFallback className={isCustomer ? 'bg-slate-200 text-slate-700 font-semibold text-xs' : 'bg-emerald-600 text-white font-semibold text-xs'}>
                        {isCustomer ? <User size={14} /> : <Bot size={14} />}
                      </AvatarFallback>
                    </Avatar>

                    <div className={`flex flex-col max-w-[80%] ${isCustomer ? 'items-end' : 'items-start'}`}>
                      <div
                        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs ${
                          isCustomer
                            ? 'bg-emerald-600 text-white rounded-tr-none'
                            : 'bg-white border border-slate-200 text-slate-900 rounded-tl-none chat-prose'
                        }`}
                      >
                        {msg.content}
                      </div>
                      <span className="text-[10px] text-slate-400 mt-1 px-1">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                )
              })}

              {submitMutation.isPending && (
                <div className="flex items-start gap-3 flex-row animate-fade-in">
                  <Avatar className="h-8 w-8 bg-emerald-600 text-white shrink-0">
                    <AvatarFallback className="bg-emerald-600 text-white">
                      <Bot size={14} />
                    </AvatarFallback>
                  </Avatar>
                  <Card className="p-3.5 border-emerald-200 bg-emerald-50/40 rounded-2xl rounded-tl-none">
                    <div className="flex items-center gap-2 text-xs font-medium text-emerald-800">
                      <RefreshCw size={14} className="animate-spin text-emerald-600" />
                      <span>Synthesizing agent reasoning & retrieving context...</span>
                    </div>
                  </Card>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="max-w-3xl mx-auto space-y-2">
            <div className="flex items-center gap-2 bg-slate-50 p-2 rounded-xl border border-slate-200 focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500 transition-all">
              <Textarea
                id="ticket-input"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
                placeholder="Type your message or ticket description..."
                rows={2}
                className="border-0 bg-transparent focus-visible:ring-0 focus-visible:outline-none shadow-none text-sm min-h-[44px]"
                disabled={submitMutation.isPending}
              />
              <Button
                id="submit-ticket"
                onClick={handleSubmit}
                disabled={!inputMessage.trim() || submitMutation.isPending}
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 h-10 font-semibold rounded-lg shrink-0 gap-1.5 shadow-sm"
              >
                <Send size={15} />
                <span>Send</span>
              </Button>
            </div>
            <p className="text-[11px] text-slate-400 text-center">
              Enter to send · Shift+Enter for line breaks
            </p>
          </div>
        </div>
      </main>

      {/* Right panel — LLM Reasoning Trace Side-by-Side */}
      <aside className="w-96 border-l border-slate-200 bg-slate-50 flex flex-col shrink-0">
        <ReasoningTracePanel events={events} connected={connected} done={done} />
      </aside>
    </div>
  )
}
