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

import { useState, useRef, useEffect } from 'react'
import { Floor3DMap } from '../../../shared/Floor3DMap'

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

  const sevColor = SEV_COLOR[incidentData?.severity] || '#ef4444'

  return (
    <div style={{
      background: '#0f172a',
      border: '1px solid #1e293b',
      borderRadius: 16,
      padding: '20px 16px',
      margin: '0 16px 16px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
    }}>
      <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16, fontFamily: "'Inter', sans-serif" }}>
        Your location: <strong style={{ color: '#f8fafc' }}>Room {yourRoom}</strong>
      </p>

      {/* Room strip */}
      <div style={{
        display: 'flex',
        gap: 6,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 24,
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
              minWidth: 48, height: 40,
              border: `1.5px solid ${isDanger ? sevColor : isYours ? '#3b82f6' : '#334155'}`,
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700,
              color: isDanger ? '#fca5a5' : isYours ? '#60a5fa' : '#64748b',
              background: isDanger ? 'rgba(220,38,38,0.1)' : isYours ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.02)',
              fontFamily: 'monospace',
              position: 'relative',
              boxShadow: isDanger ? `0 0 12px rgba(220,38,38,0.3)` : 'none',
            }}>
              {label}
              {isDanger && (
                <span style={{
                  position: 'absolute', top: -10, right: -8,
                  fontSize: 11, background: sevColor, color: '#fff',
                  borderRadius: 99, padding: '2px 6px', lineHeight: '14px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.5)'
                }}>!</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Path diagram */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-around',
        marginBottom: 20, gap: 10,
      }}>
        {/* YOU box */}
        <div style={{
          padding: '10px 16px', borderRadius: 10,
          background: 'rgba(59,130,246,0.15)', border: '1px solid #3b82f6', color: '#60a5fa',
          fontSize: 12, fontWeight: 700, fontFamily: 'monospace',
          boxShadow: '0 4px 12px rgba(59,130,246,0.2)',
        }}>
          YOU {yourRoom}
        </div>

        {/* Dashed path line */}
        <div style={{ flex: 1, position: 'relative', height: 24, display: 'flex', alignItems: 'center' }}>
          <div style={{
            width: '100%', height: 2,
            background: `repeating-linear-gradient(to right, #4ade80 0, #4ade80 8px, transparent 8px, transparent 16px)`,
          }} />
          <div style={{
            position: 'absolute', right: -6,
            width: 10, height: 10, borderTop: '2px solid #4ade80', borderRight: '2px solid #4ade80',
            transform: 'rotate(45deg)',
          }} />
        </div>

        {/* EXIT A — safe */}
        <div style={{
          padding: '10px 16px', borderRadius: 10,
          border: '1px solid #22c55e', background: 'rgba(34,197,94,0.1)',
          color: '#4ade80', fontSize: 12, fontWeight: 700, fontFamily: 'monospace',
          textAlign: 'center', boxShadow: '0 4px 12px rgba(34,197,94,0.15)',
        }}>
          {exitName}
          <div style={{ fontSize: 10, marginTop: 4, opacity: 0.8 }}>SAFE</div>
        </div>

        {/* EXIT B — blocked */}
        {blockageNote && (
          <div style={{
            padding: '10px 16px', borderRadius: 10,
            border: '1px solid #ef4444', background: 'rgba(239,68,68,0.1)',
            color: '#fca5a5', fontSize: 12, fontWeight: 700, fontFamily: 'monospace',
            textAlign: 'center', position: 'relative', overflow: 'hidden'
          }}>
            EXIT B
            <div style={{ fontSize: 10, marginTop: 4, opacity: 0.8 }}>BLOCKED</div>
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              fontSize: 32, color: '#ef4444', opacity: 0.15, pointerEvents: 'none',
            }}>✕</div>
          </div>
        )}
      </div>

      {/* Distance + blocking note */}
      <div style={{ textAlign: 'center', marginTop: 16 }}>
        <p style={{ fontSize: 13, color: '#94a3b8', fontFamily: "'Inter', sans-serif" }}>
          Estimated distance to {exitName}: <strong style={{ color: '#e2e8f0' }}>{distance}</strong>
        </p>
        {blockageNote && (
          <p style={{ fontSize: 12, color: '#fca5a5', marginTop: 4, fontWeight: 500 }}>{blockageNote}</p>
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
      background: '#0f172a',
      border: '1px solid #1e293b',
      borderRadius: 16,
      padding: '16px 20px',
      margin: '0 16px 16px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
    }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 10,
        padding: '6px 14px', background: 'rgba(34,197,94,0.1)',
        border: '1px solid rgba(34,197,94,0.2)', borderRadius: 99,
        marginBottom: 16,
      }}>
        <span style={{ fontSize: 14 }}>🚶</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#4ade80', letterSpacing: 0.5 }}>
          HEAD TO {exitName.toUpperCase()}
        </span>
      </div>

      <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {steps.map((step, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <span style={{
              minWidth: 24, height: 24, borderRadius: '50%',
              background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, color: '#60a5fa', fontWeight: 700, fontFamily: 'monospace',
              flexShrink: 0, marginTop: 2,
            }}>{i + 1}</span>
            <span style={{ fontSize: 14, color: '#e2e8f0', lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>
              {step}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}


// Floor3DMap is imported from shared components

// Medical emergency specific view
function MedicalCard({ incidentData }) {
  const staffNames = incidentData?.assigned_staff_names?.length > 0 
    ? incidentData.assigned_staff_names.join(' and ') 
    : 'Our staff';
    
  const exitName = incidentData?.exit_name || 'the nearest exit';
  const isHighSeverity = incidentData?.severity === 'CRITICAL' || incidentData?.severity === 'HIGH';

  return (
    <div style={{
      background: '#0f172a',
      border: '1px solid #1e293b',
      borderRadius: 16,
      padding: '24px 20px',
      margin: '0 16px 16px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 36, marginBottom: 16, filter: 'drop-shadow(0 0 10px rgba(239,68,68,0.5))' }}>⚕️</div>
      <h3 style={{ margin: '0 0 10px 0', color: '#f8fafc', fontSize: 18, fontFamily: "'Inter', sans-serif", fontWeight: 700 }}>
        Help is on the way
      </h3>
      <p style={{ margin: '0 0 20px 0', color: '#94a3b8', fontSize: 14, fontFamily: "'Inter', sans-serif", lineHeight: 1.5 }}>
        <strong style={{ color: '#e2e8f0' }}>{staffNames}</strong> will be with you shortly{isHighSeverity ? ` to escort you safely to ${exitName}` : ''}.
      </p>

      {isHighSeverity && (
        <div style={{
          background: 'rgba(220,38,38,0.1)',
          border: '1px solid rgba(220,38,38,0.3)',
          borderRadius: 12,
          padding: '16px',
          marginBottom: '20px',
          color: '#fca5a5',
          fontSize: 14,
          fontWeight: 600,
          fontFamily: "'Inter', sans-serif",
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          boxShadow: 'inset 0 0 20px rgba(220,38,38,0.05)'
        }}>
          <span style={{ fontSize: 18 }}>🚑</span>
          An ambulance has been dispatched to {exitName}.
        </div>
      )}

      <div style={{
        background: 'rgba(255,255,255,0.03)',
        borderRadius: 12,
        padding: '20px',
        border: '1px solid rgba(255,255,255,0.05)',
        textAlign: 'left'
      }}>
        <h4 style={{ margin: '0 0 12px 0', color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>
          Important Tips
        </h4>
        <ul style={{ margin: 0, padding: '0 0 0 20px', color: '#cbd5e1', fontSize: 14, lineHeight: 1.6, fontFamily: "'Inter', sans-serif" }}>
          <li style={{ marginBottom: 8 }}>Please stay exactly where you are.</li>
          <li style={{ marginBottom: 8 }}>Try to remain calm and take deep breaths.</li>
          <li style={{ marginBottom: 0 }}>Unlock and open your door so our team can enter quickly.</li>
        </ul>
      </div>
    </div>
  )
}

export function AlertBanner({ incident, onDismiss }) {
  const [minimised, setMinimised] = useState(false)

  if (!incident) return null

  const sevColor = SEV_COLOR[incident.severity] || '#dc2626'
  const steps    = parseSteps(incident.steps)
  const exitName = incident.exit_name || 'EXIT A'
  const isMedical = incident.incident_type === 'medical'
  const isHighSeverity = incident.severity === 'CRITICAL' || incident.severity === 'HIGH'

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
    <div style={{ background: '#f1f5f9', overflowY: 'auto', maxHeight: '85vh' }}>
      {/* Red emergency header */}
      <div style={{
        background: `linear-gradient(135deg, ${sevColor} 0%, #7f1d1d 100%)`,
        padding: '16px 20px',
        animation: 'alert-pulse 2s ease-in-out infinite',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        boxShadow: `0 4px 20px ${sevColor}40`,
        position: 'relative',
        zIndex: 10,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', letterSpacing: 0.5, lineHeight: 1.3, fontFamily: "'Inter', sans-serif" }}>
              {isMedical ? '🚨 MEDICAL EMERGENCY' : '🚨 EVACUATION ALERT'}
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', marginTop: 4, fontFamily: "'Inter', sans-serif" }}>
              {incident.incident_type?.charAt(0).toUpperCase() + (incident.incident_type?.slice(1) || '')} detected
              {incident.full_location ? ` near ${incident.full_location}` : ''}
            </div>
          </div>
          <button
            onClick={() => setMinimised(true)}
            style={{
              background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.2)',
              color: '#fff', borderRadius: 8, padding: '6px 12px',
              cursor: 'pointer', fontSize: 11, fontFamily: 'monospace', flexShrink: 0,
              fontWeight: 600, transition: 'background 0.2s'
            }}
          >
            MINIMIZE
          </button>
        </div>
      </div>

      {/* Dynamic Content */}
      <div style={{ paddingTop: 16, background: '#020617', minHeight: '100%' }}>
        {isMedical ? (
          <>
            <MedicalCard incidentData={incident} />
            <Floor3DMap incidentData={incident} />
          </>
        ) : (
          <>
            <DirectionsCard steps={steps} exitName={exitName} />
            <Floor3DMap incidentData={incident} />
          </>
        )}
      </div>

      <style>{`@keyframes alert-pulse { 0%,100%{opacity:1} 50%{opacity:.85} }`}</style>
    </div>
  )
}
