import { useEffect, useRef, useState } from 'react'
import type { TraceEvent } from '../types'
import { apiBaseUrl } from '../lib/api'

export function useSSETrace(ticketId: string | null) {
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [done, setDone] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!ticketId) return

    setEvents([])
    setDone(false)

    const sseUrl = `${apiBaseUrl}/coordinator/tickets/${ticketId}/trace`
    const es = new EventSource(sseUrl)
    esRef.current = es

    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      try {
        const event: TraceEvent = JSON.parse(e.data)
        setEvents((prev) => [...prev, event])

        if (
          event.event_type === 'auto_resolved' ||
          event.event_type === 'escalation_triggered' ||
          event.event_type === 'handoff_packet_generated'
        ) {
          setDone(true)
          es.close()
        }
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      setConnected(false)
      setDone(true) // Mark done on error so polling fallback can retrieve results
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [ticketId])

  return { events, connected, done }
}
