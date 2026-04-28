import { useEffect, useRef, useState, useCallback } from 'react'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const RECONNECT_MS = 3000

/**
 * Connects to /ws/aria/{venueId}/staff_{staffId}
 * Calls the appropriate handler for each event type:
 *   onThreatDetected(data)
 *   onStaffAlert(data)
 *   onIncidentResolved(data)
 *   onDispatchReminder(data)
 *   onPathUpdate(data)
 */
export function useStaffSocket({
  venueId,
  staffId,
  onThreatDetected,
  onStaffAlert,
  onIncidentResolved,
  onDispatchReminder,
  onPathUpdate,
}) {
  const wsRef        = useRef(null)
  const timerRef     = useRef(null)
  const mountedRef   = useRef(true)
  const [status, setStatus] = useState('connecting')

  const sessionId = `staff_${staffId}`

  const connect = useCallback(() => {
    if (!venueId || !staffId) return

    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      } else if (wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.onopen = () => {
          if (wsRef.current) wsRef.current.close()
        }
      }
    }

    const ws = new WebSocket(`${WS_BASE}/ws/aria/${venueId}/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      setStatus('open')
      clearTimeout(timerRef.current)
    }

    ws.onmessage = (e) => {
      if (!mountedRef.current) return
      try {
        const msg = JSON.parse(e.data)
        const { event, data } = msg
        if (event === 'THREAT_DETECTED')    onThreatDetected?.(data)
        else if (event === 'STAFF_ALERT')   onStaffAlert?.(data)
        else if (event === 'INCIDENT_RESOLVED') onIncidentResolved?.(data)
        else if (event === 'DISPATCH_REMINDER') onDispatchReminder?.(data)
        else if (event === 'PATH_UPDATE')   onPathUpdate?.(data)
      } catch (_) {}
    }

    ws.onerror = () => { if (mountedRef.current) setStatus('error') }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setStatus('closed')
      timerRef.current = setTimeout(() => {
        if (mountedRef.current) { setStatus('connecting'); connect() }
      }, RECONNECT_MS)
    }
  }, [venueId, staffId])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(timerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close()
        } else if (wsRef.current.readyState === WebSocket.CONNECTING) {
          // Prevent the "closed before established" warning by waiting for open to close it
          wsRef.current.onopen = () => {
            if (wsRef.current) wsRef.current.close()
          }
        }
      }
    }
  }, [connect])

  return { status }
}