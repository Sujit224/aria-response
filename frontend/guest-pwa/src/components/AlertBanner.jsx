/**
 * AlertBanner.jsx
 * ───────────────
 * Full-screen emergency overlay that appears when a THREAT_DETECTED
 * WebSocket event is received.
 *
 * Matches the UX shown in the reference image:
 *  - Red emergency header
 *  - Mini floor corridor view showing room positions
 *  - "YOU [room]" (blue) → EXIT A (green) / EXIT B blocked (red X)
 *  - Dashed path from guest → exit
 *  - Distance + step-by-step turn-by-turn directions
 *  - Minimise button to collapse back to chat
 */

import { useState } from 'react'

const SEV_COLOR = {
  CRITICAL: '#dc2626',
  HIGH:     '#ea580c',
  MEDIUM:   '#d97706',
  LOW:      '#16a34a',
}

// Decode the steps string from FCM data payload (separator: ||)
function parseSteps(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  return raw.split('||').filter(Boolean)
}

// Parse "x1,y1;x2,y2;..." path string from FCM
function parsePath(raw) {
  if (!raw || !raw.length) return []
  if (Array.isArray(raw)) return raw
  return raw.split(';').map(p => p.split(',').map(Number))
}

// Very simple corridor visualisation — rooms as boxes in a row
function CorridorView({ incidentData, roomName }) {
  const blockageNote = incidentData?.blocked_nodes?.length
    ? 'EXIT B is blocked — use EXIT A only'
    : null

  const exitName   = incidentData?.exit_name   || 'EXIT A'
  const distance   = incidentData?.distance    || '—'
  const yourRoom   = roomName?.replace('Room ', '') || '?'
  const incidentRm = incidentData?.full_location?.match(/Room (\w+)/)?.[1] || '302'

  const sevColor = SEV_COLOR[incidentData?.severity] || '#dc2626'

  return (
    <div style={{
      background: '#fff',
      borderRadius: 14,
      padding: '16px',
      margin: '0 16px 12px',
      boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
    }}>
      <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 10, fontFamily: "'Inter', sans-serif" }}>
        Your location: <strong style={{ color: '#111' }}>Room {yourRoom}</strong>
      </p>

      {/* Room strip */}
      <div style={{
        display: 'flex',
        gap: 4,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 18,
        overflowX: 'auto',
        padding: '4px 0',
      }}>
        {/* Simulated corridor rooms */}
        {[yourRoom, String(parseInt(yourRoom)+1), String(parseInt(yourRoom)+2), incidentRm + '!', String(parseInt(yourRoom)+3)].map((rm, i) => {
          const isDanger  = rm.includes('!')
          const isYours   = rm === yourRoom
          const label     = rm.replace('!', '')
          return (
            <div key={i} style={{
              minWidth: 44, height: 36,
              border: `2px solid ${isDanger ? sevColor : isYours ? '#3b82f6' : '#e5e7eb'}`,
              borderRadius: 6,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 10, fontWeight: 700,
              color: isDanger ? sevColor : isYours ? '#3b82f6' : '#9ca3af',
              background: isDanger ? `${sevColor}15` : isYours ? '#eff6ff' : 'transparent',
              fontFamily: 'monospace',
              position: 'relative',
              boxShadow: isDanger ? `0 0 8px ${sevColor}44` : 'none',
            }}>
              {label}
              {isDanger && (
                <span style={{
                  position: 'absolute', top: -8, right: -6,
                  fontSize: 10, background: sevColor, color: '#fff',
                  borderRadius: 99, padding: '0 4px', lineHeight: '16px'
                }}>!</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Path diagram */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-around',
        marginBottom: 14, gap: 8,
      }}>
        {/* YOU box */}
        <div style={{
          padding: '8px 12px', borderRadius: 8,
          background: '#3b82f6', color: '#fff',
          fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
          boxShadow: '0 2px 8px rgba(59,130,246,0.4)',
        }}>
          YOU {yourRoom}
        </div>

        {/* Dashed path line */}
        <div style={{ flex: 1, position: 'relative', height: 24, display: 'flex', alignItems: 'center' }}>
          <div style={{
            width: '100%', height: 2,
            background: `repeating-linear-gradient(to right, #22c55e 0, #22c55e 8px, transparent 8px, transparent 14px)`,
          }} />
          <div style={{
            position: 'absolute', right: -6,
            width: 8, height: 8, borderTop: '2px solid #22c55e', borderRight: '2px solid #22c55e',
            transform: 'rotate(45deg)',
          }} />
        </div>

        {/* EXIT A — safe */}
        <div style={{
          padding: '8px 12px', borderRadius: 8,
          border: '2px solid #16a34a', background: '#f0fdf4',
          color: '#15803d', fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
          textAlign: 'center',
        }}>
          {exitName}
          <div style={{ fontSize: 9, marginTop: 2 }}>SAFE</div>
        </div>

        {/* EXIT B — blocked */}
        {blockageNote && (
          <div style={{
            padding: '8px 12px', borderRadius: 8,
            border: '2px solid #dc2626', background: '#fef2f2',
            color: '#991b1b', fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
            textAlign: 'center', position: 'relative',
          }}>
            EXIT B
            <div style={{ fontSize: 9, marginTop: 2 }}>BLOCKED</div>
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              fontSize: 22, color: '#dc2626', opacity: 0.25, pointerEvents: 'none',
            }}>✕</div>
          </div>
        )}
      </div>

      {/* Distance + blocking note */}
      <div style={{ textAlign: 'center', marginBottom: 4 }}>
        <p style={{ fontSize: 12, color: '#374151', fontFamily: "'Inter', sans-serif" }}>
          Estimated distance to {exitName}: <strong>{distance}</strong>
        </p>
        {blockageNote && (
          <p style={{ fontSize: 11, color: sevColor, marginTop: 2 }}>{blockageNote}</p>
        )}
      </div>
    </div>
  )
}

// Step-by-step turn-by-turn directions
function DirectionsCard({ steps, exitName }) {
  if (!steps?.length) return null
  return (
    <div style={{
      background: '#fff',
      borderRadius: 14,
      padding: '14px 16px',
      margin: '0 16px 12px',
      boxShadow: '0 4px 24px rgba(0,0,0,0.1)',
    }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '5px 12px', background: '#f0fdf4',
        border: '1px solid #86efac', borderRadius: 99,
        marginBottom: 12,
      }}>
        <span style={{ fontSize: 14 }}>🚶</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#15803d' }}>
          Head to {exitName}
        </span>
      </div>

      <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {steps.map((step, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{
              minWidth: 22, height: 22, borderRadius: '50%',
              background: '#eff6ff', border: '1.5px solid #bfdbfe',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, color: '#3b82f6', fontWeight: 700, fontFamily: 'monospace',
              flexShrink: 0, marginTop: 1,
            }}>{i + 1}</span>
            <span style={{ fontSize: 13, color: '#374151', lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>
              {step}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}


export function AlertBanner({ incident, onDismiss }) {
  const [minimised, setMinimised] = useState(false)

  if (!incident) return null

  const sevColor = SEV_COLOR[incident.severity] || '#dc2626'
  const steps    = parseSteps(incident.steps)
  const exitName = incident.exit_name || 'EXIT A'

  if (minimised) {
    return (
      <div
        onClick={() => setMinimised(false)}
        style={{
          margin: '8px 16px',
          padding: '10px 14px',
          background: `${sevColor}22`,
          border: `1.5px solid ${sevColor}`,
          borderRadius: 10,
          display: 'flex', alignItems: 'center', gap: 10,
          cursor: 'pointer',
          animation: 'alert-pulse 1.5s ease-in-out infinite',
        }}
      >
        <span style={{ fontSize: 18 }}>🚨</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: sevColor, fontFamily: 'monospace' }}>
            EMERGENCY – TAP TO EXPAND
          </div>
          <div style={{ fontSize: 11, color: '#374151' }}>{incident.full_location}</div>
        </div>
        <style>{`@keyframes alert-pulse { 0%,100%{opacity:1} 50%{opacity:.7} }`}</style>
      </div>
    )
  }

  return (
    <div style={{ background: '#f8fafc', overflowY: 'auto', maxHeight: '65vh' }}>
      {/* Red emergency header */}
      <div style={{
        background: `linear-gradient(135deg, ${sevColor} 0%, #b91c1c 100%)`,
        padding: '14px 16px',
        animation: 'alert-pulse 2s ease-in-out infinite',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 800, color: '#fff', letterSpacing: 0.5, lineHeight: 1.3 }}>
              🚨 EMERGENCY — EVACUATION IN PROGRESS
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.85)', marginTop: 3 }}>
              {incident.incident_type?.charAt(0).toUpperCase() + (incident.incident_type?.slice(1) || '')} detected
              {incident.full_location ? ` — ${incident.full_location}` : ''}
            </div>
          </div>
          <button
            onClick={() => setMinimised(true)}
            style={{
              background: 'rgba(255,255,255,0.2)', border: 'none',
              color: '#fff', borderRadius: 6, padding: '4px 8px',
              cursor: 'pointer', fontSize: 11, fontFamily: 'monospace', flexShrink: 0,
            }}
          >
            MIN
          </button>
        </div>
      </div>

      {/* Floor corridor + path diagram */}
      <div style={{ paddingTop: 12 }}>
        <CorridorView incidentData={incident} roomName={incident.room_name} />
        <DirectionsCard steps={steps} exitName={exitName} />
      </div>

      <style>{`@keyframes alert-pulse { 0%,100%{opacity:1} 50%{opacity:.85} }`}</style>
    </div>
  )
}
