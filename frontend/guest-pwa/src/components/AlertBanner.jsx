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


// Visual 2D map of the floor
function FloorMap({ incidentData }) {
  const canvasRef = useRef(null)
  const [pulse, setPulse] = useState(0)
  const { 
    static_grid, grid_width, grid_height, 
    guest_coord, exit_coord, path_update, 
    blocked_nodes, all_pois 
  } = incidentData

  useEffect(() => {
    const interval = setInterval(() => {
      setPulse(p => (p + 1) % 100)
    }, 50)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !static_grid || static_grid.length === 0) return
    
    const ctx = canvas.getContext('2d')
    const cellSize = Math.min(
      (window.innerWidth - 64) / grid_width,
      300 / grid_height
    )
    
    canvas.width = grid_width * cellSize
    canvas.height = grid_height * cellSize
    
    // 1. Clear with Dark Theme background
    ctx.fillStyle = '#0f172a'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    
    // 2. Draw Static Grid
    for (let y = 0; y < grid_height; y++) {
      for (let x = 0; x < grid_width; x++) {
        if (static_grid[y][x] === 1) {
          ctx.fillStyle = '#1e293b' // Wall
        } else {
          ctx.fillStyle = '#1e293b22' // Subtle walkable area
        }
        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize)
        
        ctx.strokeStyle = '#334155'
        ctx.lineWidth = 0.5
        ctx.strokeRect(x * cellSize, y * cellSize, cellSize, cellSize)
      }
    }

    // 3. Draw all POIs
    if (all_pois && all_pois.length > 0) {
      all_pois.forEach(poi => {
        const px = poi.coord_x * cellSize
        const py = poi.coord_y * cellSize
        const isGuestRoom = guest_coord && poi.coord_x === guest_coord[0] && poi.coord_y === guest_coord[1]
        const isTargetExit = exit_coord && poi.coord_x === exit_coord[0] && poi.coord_y === exit_coord[1]

        if (poi.type === 'room') {
          ctx.fillStyle = isGuestRoom ? '#3b82f633' : '#1e293b'
          ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2)
          
          if (cellSize > 14) {
            ctx.fillStyle = isGuestRoom ? '#60a5fa' : '#475569'
            ctx.font = `500 ${cellSize * 0.35}px 'Inter', sans-serif`
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText(poi.name, px + cellSize/2, py + cellSize/2)
          }
        } 
        else if (poi.type === 'medical') {
          ctx.fillStyle = '#450a0a'
          ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2)
          ctx.fillStyle = '#ef4444'
          ctx.font = `${cellSize * 0.6}px Arial`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText('➕', px + cellSize/2, py + cellSize/2)
        }
        else if (poi.type === 'medical') {
          ctx.fillStyle = '#1e3a8a'
          ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2)
          ctx.fillStyle = '#60a5fa'
          ctx.font = `${cellSize * 0.6}px Arial`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText('➕', px + cellSize/2, py + cellSize/2)
        }
        else if ((poi.type === 'exit' || poi.type === 'stairwell') && !isTargetExit) {
          ctx.fillStyle = '#064e3b'
          ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2)
          ctx.fillStyle = '#10b981'
          ctx.font = `${cellSize * 0.6}px Arial`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(poi.type === 'stairwell' ? '🪜' : '🚪', px + cellSize/2, py + cellSize/2)
        }
      })
    }
    
    // 4. Draw Evacuation Path with GLOW
    if (path_update && path_update.length > 0) {
      ctx.beginPath()
      ctx.strokeStyle = '#22c55e'
      ctx.lineWidth = cellSize * 0.35
      ctx.lineJoin = 'round'
      ctx.lineCap = 'round'
      ctx.shadowBlur = 10
      ctx.shadowColor = '#22c55e'
      ctx.setLineDash([cellSize * 0.5, cellSize * 0.3])
      
      const startX = path_update[0][0] * cellSize + cellSize / 2
      const startY = path_update[0][1] * cellSize + cellSize / 2
      ctx.moveTo(startX, startY)
      
      for (let i = 1; i < path_update.length; i++) {
        ctx.lineTo(path_update[i][0] * cellSize + cellSize / 2, path_update[i][1] * cellSize + cellSize / 2)
      }
      ctx.stroke()
      ctx.setLineDash([])
      ctx.shadowBlur = 0 // Reset shadow
    }
    
    // 5. Highlight Blocked Nodes
    if (blocked_nodes && blocked_nodes.length > 0) {
      blocked_nodes.forEach(node => {
        const nx = Array.isArray(node) ? node[0] : node.x
        const ny = Array.isArray(node) ? node[1] : node.y
        ctx.fillStyle = 'rgba(239, 68, 68, 0.4)'
        ctx.fillRect(nx * cellSize, ny * cellSize, cellSize, cellSize)
        
        ctx.strokeStyle = '#ef4444'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(nx * cellSize + 4, ny * cellSize + 4)
        ctx.lineTo((nx + 1) * cellSize - 4, (ny + 1) * cellSize - 4)
        ctx.moveTo((nx + 1) * cellSize - 4, ny * cellSize + 4)
        ctx.lineTo(nx * cellSize + 4, (ny + 1) * cellSize - 4)
        ctx.stroke()
      })
    }
    
    // 6. Draw Guest Icon (YOU) with pulsing ring
    if (guest_coord) {
      const gx = guest_coord[0] * cellSize + cellSize / 2
      const gy = guest_coord[1] * cellSize + cellSize / 2
      
      // Pulse ring
      const pulseSize = (pulse / 100) * cellSize * 2
      ctx.strokeStyle = `rgba(59, 130, 246, ${1 - pulse / 100})`
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(gx, gy, pulseSize, 0, Math.PI * 2)
      ctx.stroke()

      ctx.fillStyle = '#3b82f6'
      ctx.beginPath()
      ctx.arc(gx, gy, cellSize * 0.45, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()
    }
    
    // 7. Highlight RECOMMENDED TARGET (Exit or Aid Kit)
    if (exit_coord) {
      const ex = exit_coord[0] * cellSize
      const ey = exit_coord[1] * cellSize
      
      const isAidTarget = incidentData.threat_type === 'medical' && 
                          (incidentData.severity === 'LOW' || incidentData.severity === 'MEDIUM');

      // Glow effect for target
      ctx.shadowBlur = 15
      ctx.shadowColor = isAidTarget ? '#3b82f6' : '#22c55e'
      ctx.fillStyle = isAidTarget ? '#3b82f6' : '#22c55e'
      ctx.fillRect(ex, ey, cellSize, cellSize)
      ctx.shadowBlur = 0
      
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.strokeRect(ex, ey, cellSize, cellSize)
      
      ctx.fillStyle = '#fff'
      ctx.font = `${cellSize * 0.7}px Arial`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(isAidTarget ? '➕' : '🏃', ex + cellSize / 2, ey + cellSize / 2)

      // Tag
      ctx.fillStyle = isAidTarget ? '#3b82f6' : '#22c55e'
      ctx.font = `bold ${cellSize * 0.3}px 'Inter', sans-serif`
      ctx.fillText(isAidTarget ? 'NEAREST AID KIT' : 'RECOMMENDED EXIT', ex + cellSize/2, ey + cellSize + 10)
    }

  }, [incidentData, pulse])

  return (
    <div style={{
      margin: '0 16px 16px',
      background: '#1e293b',
      borderRadius: 16,
      padding: '20px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      border: '1px solid rgba(255,255,255,0.1)'
    }}>
      <div style={{
        width: '100%',
        marginBottom: 16,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h4 style={{ margin: 0, fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>
          Interactive Navigation Hub
        </h4>
        <div style={{ display: 'flex', gap: 16, fontSize: 10, fontWeight: 700 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#60a5fa' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6', boxShadow: '0 0 8px #3b82f6' }} /> YOU
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#4ade80' }}>
            <div style={{ 
              width: 8, height: 8, 
              background: (incidentData.threat_type === 'medical' && (incidentData.severity === 'LOW' || incidentData.severity === 'MEDIUM')) ? '#3b82f6' : '#22c55e' 
            }} /> RECOMMENDED TARGET
          </div>
        </div>
      </div>
      
      <div style={{ 
        width: '100%', 
        overflow: 'auto', 
        maxHeight: 400,
        background: '#0f172a',
        borderRadius: 12,
        border: '1px solid #334155',
        display: 'flex',
        justifyContent: 'center',
        padding: 12
      }}>
        <canvas ref={canvasRef} style={{ maxWidth: '100%', borderRadius: 4 }} />
      </div>
    </div>
  )
}

// Medical emergency specific view
function MedicalCard({ incidentData }) {
  const staffNames = incidentData?.assigned_staff_names?.length > 0 
    ? incidentData.assigned_staff_names.join(' and ') 
    : 'Our staff';
    
  const exitName = incidentData?.exit_name || 'the nearest exit';
  const isHighSeverity = incidentData?.severity === 'CRITICAL' || incidentData?.severity === 'HIGH';

  return (
    <div style={{
      background: '#fff',
      borderRadius: 14,
      padding: '20px 16px',
      margin: '0 16px 12px',
      boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>⚕️</div>
      <h3 style={{ margin: '0 0 8px 0', color: '#111', fontSize: 16, fontFamily: "'Inter', sans-serif" }}>
        Help is on the way
      </h3>
      <p style={{ margin: '0 0 16px 0', color: '#4b5563', fontSize: 14, fontFamily: "'Inter', sans-serif" }}>
        <strong>{staffNames}</strong> will be with you shortly{isHighSeverity ? ` to escort you safely to ${exitName}` : ''}.
      </p>

      {isHighSeverity && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fca5a5',
          borderRadius: 8,
          padding: '12px',
          marginBottom: '16px',
          color: '#991b1b',
          fontSize: 13,
          fontWeight: 600,
          fontFamily: "'Inter', sans-serif",
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
        }}>
          <span style={{ fontSize: 16 }}>🚑</span>
          An ambulance has been dispatched to {exitName}.
        </div>
      )}

      <div style={{
        background: '#f8fafc',
        borderRadius: 10,
        padding: '16px',
        border: '1px solid #e2e8f0',
        textAlign: 'left'
      }}>
        <h4 style={{ margin: '0 0 10px 0', color: '#1e293b', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Important Tips:
        </h4>
        <ul style={{ margin: 0, padding: '0 0 0 20px', color: '#334155', fontSize: 13, lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>
          <li style={{ marginBottom: 6 }}>Please stay exactly where you are.</li>
          <li style={{ marginBottom: 6 }}>Try to remain calm and take deep breaths.</li>
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
        background: `linear-gradient(135deg, ${sevColor} 0%, #b91c1c 100%)`,
        padding: '14px 16px',
        animation: 'alert-pulse 2s ease-in-out infinite',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 800, color: '#fff', letterSpacing: 0.5, lineHeight: 1.3 }}>
              {isMedical ? '🚨 MEDICAL EMERGENCY' : '🚨 EMERGENCY — EVACUATION IN PROGRESS'}
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

      {/* Dynamic Content: Text on Top, Map at Bottom */}
      <div style={{ paddingTop: 12 }}>
        {isMedical ? (
          <>
            <MedicalCard incidentData={incident} />
            <FloorMap incidentData={incident} />
          </>
        ) : (
          <>
            <DirectionsCard steps={steps} exitName={exitName} />
            <FloorMap incidentData={incident} />
          </>
        )}
      </div>

      <style>{`@keyframes alert-pulse { 0%,100%{opacity:1} 50%{opacity:.85} }`}</style>
    </div>
  )
}
