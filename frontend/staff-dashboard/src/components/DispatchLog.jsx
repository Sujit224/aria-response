import { useState, useEffect } from 'react'
import { ackDispatch } from '../lib/api'
import { ACK_COLOR, T } from '../lib/constants'

function elapsed(sentAt) {
  const secs = Math.floor((Date.now() - new Date(sentAt)) / 1000)
  if (secs < 60)  return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  return `${Math.floor(secs / 3600)}h ago`
}

export function DispatchLog({ incidentId, dispatches = [], onAcked }) {
  const [acking, setAcking] = useState(null)
  const [now, setNow] = useState(Date.now())

  // Tick every 5s to keep elapsed times fresh
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(t)
  }, [])

  async function handleAck(dispatchId) {
    setAcking(dispatchId)
    try {
      await ackDispatch(incidentId, dispatchId)
      onAcked?.(dispatchId)
    } catch (e) {
      console.error('[ARIA] Ack failed:', e)
    } finally {
      setAcking(null)
    }
  }

  if (!dispatches.length) {
    return (
      <div style={{ fontSize: 12, color: T.textDim, padding: '12px 0',
        fontFamily: T.mono }}>
        No dispatches yet
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {dispatches.map(d => {
        const pendingSecs = (now - new Date(d.sent_at)) / 1000
        const overdue     = d.ack_status === 'PENDING' && pendingSecs > 60
        const color       = ACK_COLOR[d.ack_status] || '#94a3b8'

        return (
          <div
            key={d.id}
            style={{
              background: overdue ? 'rgba(245,158,11,0.08)' : T.bgCard,
              border: `0.5px solid ${overdue ? 'rgba(245,158,11,0.5)' : 'rgba(59,130,246,0.12)'}`,
              borderRadius: 8,
              padding: '10px 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 10,
              animation: overdue ? 'pulse-border 1.5s ease-in-out infinite' : 'none',
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                <span style={{
                  fontSize: 10, fontFamily: T.mono, fontWeight: 600,
                  color, letterSpacing: 1,
                }}>
                  {d.ack_status}
                </span>
                {overdue && (
                  <span style={{
                    fontSize: 9, background: 'rgba(245,158,11,0.2)',
                    color: '#f59e0b', padding: '1px 6px', borderRadius: 99,
                    fontFamily: T.mono,
                  }}>
                    OVERDUE
                  </span>
                )}
              </div>
              <div style={{ fontSize: 12, color: T.textSub, fontFamily: T.sans }}>
                Staff ID: <span style={{ color: T.text, fontFamily: T.mono, fontSize: 11 }}>
                  {d.staff_id.slice(0, 8)}...
                </span>
              </div>
              <div style={{ fontSize: 11, color: T.textDim, marginTop: 2 }}>
                Sent {elapsed(d.sent_at)}
                {d.acked_at && ` · Acked ${elapsed(d.acked_at)}`}
              </div>
            </div>

            {d.ack_status === 'PENDING' && (
              <button
                onClick={() => handleAck(d.id)}
                disabled={acking === d.id}
                style={{
                  padding: '5px 12px',
                  border: '0.5px solid rgba(59,130,246,0.4)',
                  borderRadius: 6,
                  background: 'rgba(59,130,246,0.1)',
                  color: '#93c5fd',
                  fontSize: 11,
                  fontFamily: T.mono,
                  cursor: acking === d.id ? 'wait' : 'pointer',
                  letterSpacing: 1,
                  whiteSpace: 'nowrap',
                  transition: 'all .15s',
                }}
              >
                {acking === d.id ? '...' : 'ACK'}
              </button>
            )}
          </div>
        )
      })}

      <style>{`
        @keyframes pulse-border {
          0%,100% { border-color: rgba(245,158,11,0.5); }
          50%      { border-color: rgba(245,158,11,0.9); }
        }
      `}</style>
    </div>
  )
}