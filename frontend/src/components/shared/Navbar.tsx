import { Link, useLocation } from 'react-router-dom'
import { useAppStore } from '../../store/appStore'
import type { Role } from '../../types'
import { BrainCircuit, LayoutDashboard, AlertTriangle, MessageSquare, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const ROLES: { value: Role; label: string }[] = [
  { value: 'customer', label: 'Customer' },
  { value: 'agent', label: 'Support Agent' },
  { value: 'manager', label: 'Manager & Admin' },
]

export default function Navbar() {
  const { role, setRole } = useAppStore()
  const location = useLocation()

  const navLinks = [
    { to: '/', label: 'Chat Assistant', icon: MessageSquare, roles: ['customer'] as Role[] },
    { to: '/escalation', label: 'Escalations Queue', icon: AlertTriangle, roles: ['agent'] as Role[] },
    { to: '/dashboard', label: 'Analytics Dashboard', icon: LayoutDashboard, roles: ['manager'] as Role[] },
  ]

  const visibleLinks = navLinks.filter((l) => l.roles.includes(role))

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-sm">
      <div className="flex items-center justify-between h-full px-6 max-w-7xl mx-auto">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center shadow-sm group-hover:bg-emerald-700 transition-colors">
            <BrainCircuit size={18} className="text-white" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-slate-900 text-lg tracking-tight">
              Nexus
            </span>
            <Badge variant="emerald" className="gap-1 font-semibold text-[10px] px-1.5 py-0">
              <Sparkles size={10} /> LLM Support
            </Badge>
          </div>
        </Link>

        {/* Navigation Links */}
        <div className="flex items-center gap-1">
          {visibleLinks.map((link) => {
            const Icon = link.icon
            const active = location.pathname === link.to
            return (
              <Button
                key={link.to}
                asChild
                variant={active ? 'secondary' : 'ghost'}
                size="sm"
                className={active ? 'bg-slate-100 text-emerald-700 font-semibold border border-slate-200' : 'text-slate-600 hover:text-slate-900'}
              >
                <Link to={link.to} className="flex items-center gap-2">
                  <Icon size={15} />
                  {link.label}
                </Link>
              </Button>
            )
          })}
        </div>

        {/* Role Switcher */}
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-medium text-slate-500">Role:</span>
          <select
            id="role-switcher"
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer shadow-sm hover:border-slate-300 transition-colors"
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  )
}
