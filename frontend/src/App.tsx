import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAppStore } from './store/appStore'
import Navbar from './components/shared/Navbar'
import ChatIntakePage from './features/chat-intake/components/ChatIntakePage'
import EscalationViewPage from './features/escalation-view/components/EscalationViewPage'
import AnalyticsDashboardPage from './features/analytics-dashboard/components/AnalyticsDashboardPage'

function ProtectedRoute({ children, allowedRoles }: {
  children: React.ReactNode
  allowedRoles: Array<'customer' | 'agent' | 'manager'>
}) {
  const { role } = useAppStore()
  if (!allowedRoles.includes(role)) {
    const redirects = { customer: '/', agent: '/escalation', manager: '/dashboard' }
    return <Navigate to={redirects[role]} replace />
  }
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route
          path="/"
          element={
            <ProtectedRoute allowedRoles={['customer']}>
              <ChatIntakePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/escalation"
          element={
            <ProtectedRoute allowedRoles={['agent']}>
              <EscalationViewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute allowedRoles={['manager']}>
              <AnalyticsDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
