/**
 * GuestChat.jsx — The main Guest PWA screen
 *
 * Layout:
 *  ┌─────────────────────────┐
 *  │  StatusBar (room + WS)  │
 *  ├─────────────────────────┤
 *  │  AlertBanner (if threat)│  ← appears when THREAT_DETECTED
 *  ├─────────────────────────┤
 *  │  Chat message list      │  ← scrollable
 *  ├─────────────────────────┤
 *  │  [SOS] [Input] [Send]   │  ← sticky bottom
 *  └─────────────────────────┘
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { StatusBar }   from '../components/StatusBar'
import { AlertBanner } from '../components/AlertBanner'
import { ChatBubble }  from '../components/ChatBubble'
import { SOSButton }   from '../components/SOSButton'
import { useARIASocket } from '../hooks/useARIASocket'
import {
  getSessionId, getVenueId, getRoomId, getRoomName,
  autoAssignTestRoom,
} from '../lib/session'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const WELCOME = {
  id:   'welcome',
  role: 'aria',
  text: '👋 Hi! I\'m ARIA, your hotel emergency assistant.\n\nYou can report any concern here — medical, fire, security, or anything unusual. In an emergency, press and hold the SOS button.',
  ts:   Date.now(),
}

export function GuestChat() {
  const [messages,   setMessages]   = useState([WELCOME])
  const [input,      setInput]      = useState('')
  const [incident,   setIncident]   = useState(null)
  const [sending,    setSending]    = useState(false)
  const [fcmReady,   setFcmReady]   = useState(false)
  const [roomId,     setRoomIdState]   = useState(() => getRoomId())
  const [roomName,   setRoomNameState] = useState(() => getRoomName() || 'Assigning room…')
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)

  const sessionId = getSessionId()
  const venueId   = getVenueId()

  // ── Listen for PWA Install Prompt ──────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      e.preventDefault()
      setDeferredPrompt(e)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const handleInstallClick = async () => {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    if (outcome === 'accepted') {
      setDeferredPrompt(null)
    }
  }

  // ── Fetch room name if we have an ID but no name ───────────────
  useEffect(() => {
    if (roomId && (!roomName || roomName === 'Unknown Room' || roomName === 'Assigning room…')) {
      fetch(`${API}/map/pois/${roomId}`)
        .then(res => res.json())
        .then(data => {
          if (data.name) {
            setRoomNameState(data.name)
            localStorage.setItem('aria_room_name', data.name)
          }
        })
        .catch(err => console.warn('[ARIA] Failed to fetch room info:', err))
    }
  }, [roomId])

  // ── Auto-assign a random test room if none is set ───────────────
  useEffect(() => {
    if (roomId) return
    autoAssignTestRoom().then(id => {
      if (id) {
        setRoomIdState(id)
        setRoomNameState(getRoomName())
      }
    })
  }, [])


  // ── WebSocket ───────────────────────────────────────────────────
  const onChatAck = useCallback((data) => {
    setMessages(prev => [...prev, {
      id:   `ack-${Date.now()}`,
      role: 'aria',
      text: data.message || 'Message received.',
      ts:   Date.now(),
    }])
    setSending(false)
  }, [])

  const onThreatDetected = useCallback((data) => {
    // Build incident context for AlertBanner
    setIncident(prev => ({
      ...prev,
      incident_id:   data.incident_id,
      incident_type: data.type?.toLowerCase(),
      severity:      data.severity,
      full_location: data.full_location,
      exit_name:     data.zone_name || 'EXIT A',
      blocked_nodes: data.blocked_nodes || [],
      path_update:   data.path_update || [],
      assigned_staff_names: data.assigned_staff_names || [],
      static_grid:   data.static_grid || [],
      grid_width:    data.grid_width || 0,
      grid_height:   data.grid_height || 0,
      guest_coord:   data.guest_coord || [0,0],
      exit_coord:    data.exit_coord || [0,0],
      all_pois:      data.all_pois || [],
      room_name:     roomName,
      // steps will arrive via FCM push notification (data payload)
      // or via the chat ack message below
      steps: data.steps || prev?.steps || [],
    }))

    const isMedical = data.type?.toLowerCase() === 'medical'
    const staffNames = data.assigned_staff_names && data.assigned_staff_names.length > 0 
      ? data.assigned_staff_names.join(' and ') 
      : 'Our staff'

    const messageText = isMedical 
      ? `🚨 MEDICAL EMERGENCY\n\nHelp is on the way. ${staffNames} will be with you shortly.\n\nPlease stay where you are, do not panic, and leave the door open.`
      : `🚨 EMERGENCY ALERT\n\nA ${data.type?.toLowerCase() || 'safety'} incident has been detected near your location.\n\nPlease follow the evacuation instructions above. Head to the nearest safe exit immediately.`

    setMessages(prev => [...prev, {
      id:   `threat-${Date.now()}`,
      role: 'aria',
      text: messageText,
      ts:   Date.now(),
    }])
  }, [roomName])

  const onPathUpdate = useCallback((data) => {
    setIncident(prev => prev ? {
      ...prev,
      path_update:   data.path_update || [],
      blocked_nodes: data.blocked_nodes || [],
    } : null)

    setMessages(prev => [...prev, {
      id:   `path-${Date.now()}`,
      role: 'aria',
      text: '⚠️ The evacuation route has been updated due to changing conditions. Please follow the new path shown above.',
      ts:   Date.now(),
    }])
  }, [])

  const { status, send } = useARIASocket({
    venueId,
    sessionId,
    roomId,
    onChatAck,
    onThreatDetected,
    onPathUpdate,
    onError: (err) => {
      setMessages(prev => [...prev, {
        id:   `err-${Date.now()}`,
        role: 'aria',
        text: `⚠️ Communication error: ${err?.message || 'Unknown error'}`,
        ts:   Date.now(),
      }])
      setSending(false)
    },
  })

  // ── Auto-scroll on new message ──────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── FCM token registration ──────────────────────────────────────
  useEffect(() => {
    if (!roomId || !getGuestPhone()) return

    async function registerFCM() {
      try {
        const { initializeApp }   = await import('firebase/app')
        const { getMessaging, getToken, onMessage } = await import('firebase/messaging')

        const firebaseConfig = {
          apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
          authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
          projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
          storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
          messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
          appId:             import.meta.env.VITE_FIREBASE_APP_ID,
        }

        const firebaseApp = initializeApp(firebaseConfig, 'guest-pwa')
        const messaging   = getMessaging(firebaseApp)

        const perm = await Notification.requestPermission()
        if (perm !== 'granted') return

        const token = await getToken(messaging, {
          vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
        })

        if (token) {
          // Register token with backend
          const phone = getGuestPhone()
          await fetch(`${API}/occupants/${roomId}/fcm_token`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, fcm_token: token }),
          })
          setFcmReady(true)

          // Handle foreground FCM messages
          onMessage(messaging, (payload) => {
            const d = payload.data || {}
            if (d.incident_id) {
              setIncident(prev => ({
                ...prev,
                incident_id:   d.incident_id,
                incident_type: d.incident_type,
                severity:      d.severity,
                full_location: d.full_location,
                exit_name:     d.exit_name,
                distance:      d.distance,
                steps:         d.steps?.split('||').filter(Boolean) || [],
                room_name:     roomName,
              }))
            }
          })
        }
      } catch (e) {
        console.warn('[ARIA-FCM] Push notification setup failed:', e)
      }
    }

    registerFCM()
  }, [roomId, roomName])

  // ── Send message ────────────────────────────────────────────────
  function handleSend() {
    const text = input.trim()
    if (!text || sending || status !== 'open') return

    setMessages(prev => [...prev, {
      id:   `guest-${Date.now()}`,
      role: 'guest',
      text,
      ts:   Date.now(),
    }])
    setInput('')
    setSending(true)
    send(text)
    inputRef.current?.focus()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSOS() {
    const text = 'EMERGENCY — I need immediate help!'
    setMessages(prev => [...prev, {
      id:   `sos-${Date.now()}`,
      role: 'guest',
      text,
      ts:   Date.now(),
    }])
    setSending(true)
    send(text)
  }

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100dvh', background: '#020617', // tailwind slate-950
      color: '#f8fafc', overflow: 'hidden',
    }}>
      {/* Top bar */}
      <StatusBar
        wsStatus  = {status}
        roomName  = {roomName}
        floorInfo = {venueId ? `Venue ${venueId.slice(0, 6)}…` : null}
      />

      {/* ARIA wordmark */}
      <div style={{
        padding: '10px 16px 6px',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, fontWeight: 800, color: '#fff', fontFamily: 'monospace',
          boxShadow: '0 0 12px rgba(59,130,246,0.4)',
        }}>A</div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 2, color: '#e2f0ff', fontFamily: 'monospace' }}>ARIA</div>
          <div style={{ fontSize: 10, color: '#475569', letterSpacing: 1 }}>Emergency Assistant</div>
        </div>
        {fcmReady && (
          <div style={{
            marginLeft: 'auto', fontSize: 9, color: '#22c55e',
            fontFamily: 'monospace', letterSpacing: 1,
            background: 'rgba(34,197,94,0.1)', padding: '4px 8px',
            borderRadius: 99, border: '0.5px solid rgba(34,197,94,0.3)',
          }}>
            🔔 PUSH ON
          </div>
        )}
        {deferredPrompt && (
          <button
            onClick={handleInstallClick}
            style={{
              marginLeft: fcmReady ? 8 : 'auto', 
              fontSize: 10, color: '#3b82f6', fontWeight: 'bold',
              fontFamily: 'monospace', letterSpacing: 1,
              background: 'rgba(59,130,246,0.1)', padding: '4px 10px',
              borderRadius: 99, border: '0.5px solid rgba(59,130,246,0.3)',
              cursor: 'pointer', outline: 'none'
            }}
          >
            ⬇️ INSTALL
          </button>
        )}
      </div>

      {/* Emergency overlay */}
      {incident && (
        <AlertBanner incident={incident} onDismiss={() => setIncident(null)} />
      )}

      {/* Chat message list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 14px', display: 'flex', flexDirection: 'column' }}>
        {messages.map(msg => (
          <ChatBubble key={msg.id} message={msg} />
        ))}
        {sending && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 8 }}>
            <div style={{
              padding: '10px 16px', borderRadius: '4px 16px 16px 16px',
              background: 'rgba(59,130,246,0.08)',
              border: '0.5px solid rgba(59,130,246,0.2)',
            }}>
              <span style={{ display: 'inline-flex', gap: 4 }}>
                {[0,1,2].map(i => (
                  <span key={i} style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: '#3b82f6',
                    animation: `dot-bounce 1s ${i*0.2}s ease-in-out infinite`,
                    display: 'inline-block',
                  }} />
                ))}
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{
        padding: '10px 14px 14px',
        background: 'rgba(5,10,15,0.98)',
        borderTop: '0.5px solid rgba(59,130,246,0.12)',
        display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0,
      }}>
        <SOSButton onSOS={handleSOS} disabled={status !== 'open'} />

        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your situation or ask for help…"
          rows={1}
          style={{
            flex: 1,
            background: 'rgba(255,255,255,0.05)',
            border: '0.5px solid rgba(59,130,246,0.25)',
            borderRadius: 12,
            padding: '11px 14px',
            color: '#e2f0ff',
            fontSize: 14,
            fontFamily: "'Inter', system-ui, sans-serif",
            resize: 'none',
            outline: 'none',
            lineHeight: 1.4,
            maxHeight: 96,
            overflowY: 'auto',
          }}
        />

        <button
          onClick={handleSend}
          disabled={!input.trim() || sending || status !== 'open'}
          style={{
            width: 44, height: 44, borderRadius: 12,
            background: (!input.trim() || sending || status !== 'open')
              ? 'rgba(59,130,246,0.15)'
              : 'linear-gradient(135deg, #2563eb, #3b82f6)',
            border: '0.5px solid rgba(59,130,246,0.3)',
            color: '#fff', fontSize: 18,
            cursor: (!input.trim() || status !== 'open') ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            boxShadow: (!input.trim() || status !== 'open') ? 'none' : '0 0 12px rgba(59,130,246,0.4)',
            transition: 'all .15s',
          }}
        >
          ↑
        </button>
      </div>

      <style>{`
        @keyframes dot-bounce {
          0%,80%,100% { transform: translateY(0); opacity: .4 }
          40%          { transform: translateY(-5px); opacity: 1 }
        }
      `}</style>
    </div>
  )
}

// Helper re-import
function getGuestPhone() {
  return localStorage.getItem('aria_guest_phone') || ''
}
