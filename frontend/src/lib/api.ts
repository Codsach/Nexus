import axios from 'axios'

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
// Normalize apiBaseUrl (ensure no trailing slash)
const apiBaseUrl = rawBaseUrl.replace(/\/$/, '')
const hostUrl = apiBaseUrl.replace(/\/api\/v1$/, '')

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
})

export default api

// ---- Coordinator ----
export const submitTicket = (customerId: string, message: string) =>
  api.post('/coordinator/tickets', { customer_id: customerId, message })

export const getTicket = (ticketId: string) =>
  api.get(`/coordinator/tickets/${ticketId}`)

export const listTickets = () =>
  api.get('/coordinator/tickets')

// ---- Escalation ----
export const getEscalatedTickets = () =>
  api.get('/escalation/tickets')

export const getHandoffPacket = (ticketId: string) =>
  api.get(`/escalation/${ticketId}/packet`)

// ---- Analytics ----
export const getAnalyticsOverview = () =>
  api.get('/analytics/overview')

export const getAnalyticsClusters = () =>
  api.get('/analytics/clusters')

export const getChurnRisk = () =>
  api.get('/analytics/churn-risk')

// ---- Mock Systems ----
export const getMockCustomers = () =>
  api.get('/mock/customers')

export const getMockCRM = (customerId: string) =>
  api.get(`/mock/crm/${customerId}`)

export const getMockBilling = (customerId: string) =>
  api.get(`/mock/billing/${customerId}`)

export const getMockOrders = (customerId: string) =>
  api.get(`/mock/orders/${customerId}`)

export const resetMockData = () =>
  api.post('/mock/reset')

// ---- Knowledge ----
export const searchKnowledge = (q: string) =>
  api.get('/knowledge/search', { params: { q, top_k: 5 } })

// ---- Health ----
export const getHealth = () =>
  axios.get(`${hostUrl}/health`)

