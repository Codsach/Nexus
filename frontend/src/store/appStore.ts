import { create } from 'zustand'
import type { Role } from '../types'

interface AppState {
  role: Role
  setRole: (role: Role) => void
  activeTicketId: string | null
  setActiveTicketId: (id: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  role: 'customer',
  setRole: (role) => set({ role }),
  activeTicketId: null,
  setActiveTicketId: (id) => set({ activeTicketId: id }),
}))
