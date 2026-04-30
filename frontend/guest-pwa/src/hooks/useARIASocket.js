/**
 * useARIASocket.js
 * ─────────────────
 * WebSocket hook for the Guest PWA.
 * Connects to ws://backend/ws/aria/{venueId}/{sessionId}
 *
 * Features:
 *  - Exponential-backoff auto-reconnect
 *  - 25-second keep-alive ping
 *  - Event routing to typed callbacks
 *  - Sends message payload with room_id + language
 */

import { useEffect, useRef, useState, useCallback } from 'react'

const WS_BASE        = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const RECONNECT_BASE = 1_000    // ms
const RECONNECT_MAX  = 30_000   // ms cap

export function useARIASocket({
  venueId,
  sessionId,
  roomId,
  language = 'en',
  onChatAck,
  onThreatDetected,
  onPathUpdate,
  onError,
}) {
  const wsRef       = useRef(null)
  const timerRef    = useRef(null)
  const keepAliveRef = useRef(null)
  const mountedRef  = useRef(true)
  const attemptsRef = useRef(0)
  const [status, setStatus] = useState('connecting')

  const send = useCallback((rawText) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        session_id: sessionId,
        raw_text:   rawText,
        room_id:    roomId,
        venue_id:   venueId,
        language,
      }))
    }
  }, [sessionId, roomId, venueId, language])

  const connect = useCallback(() => {
    if (!venueId || !sessionId) return
    if (wsRef.current) {
      const oldWs = wsRef.current
      oldWs.onclose = null
      oldWs.onerror = null
      if (oldWs.readyState === WebSocket.OPEN) {
        oldWs.close()
      } else if (oldWs.readyState === WebSocket.CONNECTING) {
        oldWs.onopen = () => {
          oldWs.close()
        }
      }
    }

    const ws = new WebSocket(`${WS_BASE}/ws/aria/${venueId}/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      attemptsRef.current = 0
      setStatus('open')
      clearTimeout(timerRef.current)

      // Keep-alive ping every 25s (before server 30s timeout)
      clearInterval(keepAliveRef.current)
      keepAliveRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ raw_text: '__ping__', venue_id: venueId, session_id: sessionId }))
        }
      }, 25_000)
    }

    ws.onmessage = (e) => {
      if (!mountedRef.current) return
      try {
        const { event, data } = JSON.parse(e.data)
        if      (event === 'CHAT_ACK')        onChatAck?.(data)
        else if (event === 'THREAT_DETECTED') onThreatDetected?.(data)
        else if (event === 'PATH_UPDATE')     onPathUpdate?.(data)
        else if (event === 'error')           onError?.(data)
      } catch (_) {}
    }

    ws.onerror = () => {
      if (mountedRef.current) setStatus('error')
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      clearInterval(keepAliveRef.current)
      setStatus('closed')
      const delay = Math.min(RECONNECT_BASE * 2 ** attemptsRef.current, RECONNECT_MAX)
      attemptsRef.current++
      timerRef.current = setTimeout(() => {
        if (mountedRef.current) {
          setStatus('connecting')
          connect()
        }
      }, delay)
    }
  }, [venueId, sessionId])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(timerRef.current)
      clearInterval(keepAliveRef.current)
      if (wsRef.current) {
        const oldWs = wsRef.current
        oldWs.onclose = null
        oldWs.onerror = null
        if (oldWs.readyState === WebSocket.OPEN) {
          oldWs.close()
        } else if (oldWs.readyState === WebSocket.CONNECTING) {
          // Prevent the "closed before established" warning by waiting for open to close it
          oldWs.onopen = () => {
            oldWs.close()
          }
        }
      }
    }
  }, [connect])

  return { status, send }
}
