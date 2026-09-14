import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts'
import {
  LayoutDashboard, TrendingUp, AlertTriangle, RefreshCw, TrendingDown, Minus, CheckCircle2, ArrowUpRight, ShieldAlert, Database
} from 'lucide-react'
import {
  getAnalyticsOverview, getAnalyticsClusters, getChurnRisk,
  getMockCustomers, resetMockData,
} from '../../../lib/api'
import type { AnalyticsOverview, ClusterItem, ChurnRiskItem } from '../../../types'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Table, TableHeader, TableBody, TableHead, TableRow, TableCell
} from '@/components/ui/table'

const CHART_COLORS = ['#059669', '#0d9488', '#d97706', '#ea580c', '#e11d48', '#64748b']

const RISK_BADGE: Record<string, 'rose' | 'amber' | 'emerald' | 'slate'> = {
  critical: 'rose',
  high: 'amber',
  medium: 'amber',
}

const TREND_ICON: Record<string, React.ReactNode> = {
  rising: <TrendingUp size={14} className="text-rose-600" />,
  falling: <TrendingDown size={14} className="text-emerald-600" />,
  stable: <Minus size={14} className="text-slate-400" />,
}

function MetricCard({ label, value, sub, valueColor = 'text-slate-900' }: {
  label: string; value: string | number; sub?: string; valueColor?: string
}) {
  return (
    <Card className="border-slate-200 bg-white">
      <CardContent className="p-4 space-y-1">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</span>
        <div className={`text-2xl font-extrabold ${valueColor}`}>{value}</div>
        {sub && <span className="text-[11px] text-slate-500 font-medium">{sub}</span>}
      </CardContent>
    </Card>
  )
}

function OverviewTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: getAnalyticsOverview,
    refetchInterval: 10000,
  })
  const overview: AnalyticsOverview | null = data?.data || null

  if (isLoading || !overview) return (
    <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Loading analytics overview...</div>
  )

  const monthData = Object.entries(overview.tickets_by_month).map(([month, count]) => ({
    month: month.slice(5), count
  }))

  const intentData = Object.entries(overview.intent_breakdown).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1), value
  }))

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Total Tickets" value={overview.total_tickets} sub="All time volume" />
        <MetricCard
          label="Resolution Rate"
          value={`${overview.resolution_rate_pct}%`}
          sub="Auto-resolved by LLM"
          valueColor="text-emerald-600"
        />
        <MetricCard
          label="Escalation Rate"
          value={`${overview.escalation_rate_pct}%`}
          sub="Requires human handoff"
          valueColor={overview.escalation_rate_pct > 30 ? 'text-rose-600' : 'text-amber-600'}
        />
        <MetricCard
          label="Avg Resolution"
          value={`${overview.avg_resolution_time_minutes}m`}
          sub="End-to-end processing time"
          valueColor="text-teal-600"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Line Chart Card */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="py-4 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900">
              Monthly Ticket Volume
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={monthData}>
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <RechartsTooltip
                  contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, color: '#0f172a', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                />
                <Line type="monotone" dataKey="count" stroke="#059669" strokeWidth={2.5} dot={{ fill: '#059669', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Pie Chart Card */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="py-4 border-b border-slate-100">
            <CardTitle className="text-sm font-bold text-slate-900">
              Issues Breakdown by Type
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={intentData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }: { name?: string; percent?: number }) =>
                  `${name || ''} ${((percent || 0) * 100).toFixed(0)}%`
                } labelLine={false}>
                  {intentData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, color: '#0f172a' }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Status Breakdown row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-slate-200 bg-emerald-50/40">
          <CardContent className="p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
              <CheckCircle2 size={20} className="text-emerald-700" />
            </div>
            <div>
              <p className="text-xl font-extrabold text-emerald-800">{overview.resolved}</p>
              <p className="text-xs font-medium text-slate-600">Successfully Auto-Resolved</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-amber-50/40">
          <CardContent className="p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
              <AlertTriangle size={20} className="text-amber-700" />
            </div>
            <div>
              <p className="text-xl font-extrabold text-amber-800">{overview.escalated}</p>
              <p className="text-xs font-medium text-slate-600">Escalated to Human Agents</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-teal-50/40">
          <CardContent className="p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-teal-100 flex items-center justify-center shrink-0">
              <ArrowUpRight size={20} className="text-teal-700" />
            </div>
            <div>
              <p className="text-xl font-extrabold text-teal-800">{overview.open}</p>
              <p className="text-xs font-medium text-slate-600">Active / In Investigation</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ClustersTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-clusters'],
    queryFn: getAnalyticsClusters,
    refetchInterval: 30000,
  })
  const clusters: ClusterItem[] = data?.data || []

  if (isLoading) return <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Loading clusters...</div>

  const chartData = clusters.map((c) => ({ name: c.cluster_label.split(' ')[0], count: c.ticket_count }))

  return (
    <div className="space-y-6 animate-fade-in">
      <Card className="border-slate-200 bg-white">
        <CardHeader className="py-4 border-b border-slate-100">
          <CardTitle className="text-sm font-bold text-slate-900">
            Recurring Issue Cluster Volume
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <RechartsTooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, color: '#0f172a' }} />
              <Bar dataKey="count" fill="#059669" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {clusters.map((c) => (
          <Card key={c.cluster_label} className="border-slate-200 bg-white">
            <CardHeader className="py-4 pb-2 flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-base font-bold text-slate-900">
                  {c.cluster_label}
                </CardTitle>
                <p className="text-xs text-slate-500 mt-0.5">{c.ticket_count} tickets detected</p>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                {TREND_ICON[c.trend_direction]}
                <span className="capitalize">{c.trend_direction} Trend</span>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-2">
              <p className="text-sm text-slate-700 leading-relaxed mb-3">
                {c.trend_narrative}
              </p>
              {c.example_issues.length > 0 && (
                <div className="space-y-1 bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Example Reported Issues</span>
                  {c.example_issues.slice(0, 2).map((issue, i) => (
                    <p key={i} className="text-xs text-slate-600 font-medium">• {issue}</p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function ChurnRiskTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['churn-risk'],
    queryFn: getChurnRisk,
    refetchInterval: 30000,
  })
  const customers: ChurnRiskItem[] = data?.data || []

  if (isLoading) return <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Loading churn analysis...</div>

  return (
    <div className="space-y-4 animate-fade-in">
      <Card className="border-amber-200 bg-amber-50/40">
        <CardContent className="p-4 flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
          <p className="text-xs text-slate-700 leading-relaxed font-medium">
            Customer churn risk is evaluated automatically from issue frequency, sentiment trend, and account status.
          </p>
        </CardContent>
      </Card>

      {customers.length === 0 && (
        <div className="text-center py-8 text-slate-400 text-sm">No at-risk customers detected</div>
      )}

      {customers.map((c) => (
        <Card key={c.customer_id} className="border-slate-200 bg-white">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 text-base">{c.customer_name}</span>
                  <Badge
                    variant={c.tier === 'Enterprise' ? 'amber' : c.tier === 'Premium' ? 'emerald' : 'slate'}
                    className="text-[10px] font-medium px-2 py-0"
                  >
                    {c.tier}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{c.customer_id} · ${c.total_spend_usd.toLocaleString()} LTV</p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <Badge variant={RISK_BADGE[c.risk_level] || 'amber'} className="text-xs uppercase px-2 py-0.5">
                  {c.risk_level} Risk
                </Badge>
                <span className="text-xs font-semibold text-slate-500">Score: {c.risk_score}/100</span>
              </div>
            </div>

            {/* Risk Bar */}
            <div className="mb-3">
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    c.risk_level === 'critical' ? 'bg-rose-500' :
                    c.risk_level === 'high' ? 'bg-amber-500' : 'bg-emerald-500'
                  }`}
                  style={{ width: `${c.risk_score}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <div className="text-center">
                <p className="text-lg font-bold text-slate-900">{c.ticket_count}</p>
                <p className="text-[11px] text-slate-500">Total Tickets</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-amber-600">{c.negative_tickets}</p>
                <p className="text-[11px] text-slate-500">Negative Sentiment</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-rose-600">{c.unresolved_tickets}</p>
                <p className="text-[11px] text-slate-500">Unresolved</p>
              </div>
            </div>

            {c.sentiment_trend.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="font-medium">Sentiment Trend:</span>
                {c.sentiment_trend.map((s, i) => (
                  <span key={i} className="text-sm">
                    {s === 'very_negative' ? '😡' : s === 'negative' ? '😞' : s === 'neutral' ? '😐' : '😊'}
                  </span>
                ))}
              </div>
            )}

            {c.notes && (
              <p className="text-xs text-slate-500 mt-2.5 border-t border-slate-100 pt-2 font-medium">
                Note: {c.notes}
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function MockDataAdminTab() {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['mock-customers'],
    queryFn: getMockCustomers,
  })

  const resetMutation = useMutation({
    mutationFn: resetMockData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mock-customers'] })
    },
  })

  const customers = data?.data || []

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-slate-900 text-base">Mock Enterprise Records</h3>
          <p className="text-xs text-slate-500 mt-0.5">Inspect fixture records for CRM, Billing, and Order history</p>
        </div>
        <Button
          id="reset-mock-data"
          onClick={() => resetMutation.mutate()}
          disabled={resetMutation.isPending}
          variant="outline"
          size="sm"
          className="gap-2 text-xs font-semibold border-slate-200"
        >
          <RefreshCw size={14} className={resetMutation.isPending ? 'animate-spin' : ''} />
          Reset Seed Data
        </Button>
      </div>

      {resetMutation.isSuccess && (
        <Card className="border-emerald-200 bg-emerald-50/50 p-3">
          <p className="text-xs font-semibold text-emerald-800">✅ Mock fixture data reset to seed state successfully</p>
        </Card>
      )}

      {/* Customer Table using shadcn Table */}
      <Card className="border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs font-bold text-slate-500">ID</TableHead>
              <TableHead className="text-xs font-bold text-slate-500">Name</TableHead>
              <TableHead className="text-xs font-bold text-slate-500">Tier</TableHead>
              <TableHead className="text-xs font-bold text-slate-500">Status</TableHead>
              <TableHead className="text-xs font-bold text-slate-500">LTV</TableHead>
              <TableHead className="text-xs font-bold text-slate-500">Joined</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((c: any) => (
              <TableRow key={c.customer_id}>
                <TableCell className="font-mono text-xs font-semibold text-emerald-700">{c.customer_id}</TableCell>
                <TableCell className="font-semibold text-slate-900 text-xs">{c.name}</TableCell>
                <TableCell>
                  <Badge
                    variant={c.tier === 'Enterprise' ? 'amber' : c.tier === 'Premium' ? 'emerald' : 'slate'}
                    className="text-[10px] font-medium"
                  >
                    {c.tier}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={c.account_status === 'active' ? 'emerald' : c.account_status === 'suspended' ? 'rose' : 'amber'}
                    className="text-[10px] capitalize"
                  >
                    {c.account_status}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs font-medium text-slate-700">${c.total_spend_usd.toLocaleString()}</TableCell>
                <TableCell className="text-xs text-slate-500">{c.join_date}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

export default function AnalyticsDashboardPage() {
  const [activeTab, setActiveTab] = useState<string>('overview')

  return (
    <div className="mt-16 min-h-[calc(100vh-64px)] bg-slate-50 text-slate-900 font-sans pb-12">
      {/* Dashboard Sticky Header */}
      <div className="border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-16 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center border border-slate-200">
              <LayoutDashboard size={18} className="text-emerald-700" />
            </div>
            <h1 className="font-bold text-slate-900 text-base">Analytics Studio</h1>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-auto">
            <TabsList className="bg-slate-100 border border-slate-200">
              <TabsTrigger value="overview" id="tab-overview" className="text-xs px-3">
                Overview
              </TabsTrigger>
              <TabsTrigger value="clusters" id="tab-recurring-issues" className="text-xs px-3">
                Recurring Issues
              </TabsTrigger>
              <TabsTrigger value="churn" id="tab-churn-risk" className="text-xs px-3">
                Churn Risk
              </TabsTrigger>
              <TabsTrigger value="admin" id="tab-mock-data-admin" className="text-xs px-3">
                Mock Data Admin
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Main Content Body */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'clusters' && <ClustersTab />}
        {activeTab === 'churn' && <ChurnRiskTab />}
        {activeTab === 'admin' && <MockDataAdminTab />}
      </div>
    </div>
  )
}
