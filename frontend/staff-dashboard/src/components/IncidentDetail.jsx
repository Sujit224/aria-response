import { useEffect, useState } from 'react'
import { Floor3DMap } from '../../../shared/Floor3DMap'
import { DispatchLog } from './DispatchLog'
import { getIncident, getFloorMap, getFloorCameras, resolveIncident } from '../lib/api'
import { SEV_COLOR, SEV_LABEL, THREAT_LABEL, THREAT_ICON, T } from '../lib/constants'

export function IncidentDetail({ incident, livePathUpdate, liveBlockedNodes, onResolved }) {
  const [detail,   setDetail]   = useState(null)
  const [floorData, setFloor]   = useState(null)
  const [cameras,  setCameras]  = useState([])
  const [dispatches, setDispatches] = useState([])
  const [resolving, setResolving]   = useState(false)
  const [loading,   setLoading]     = useState(true)

  useEffect(() => {
    if (!incident) return
    setLoading(true)
    load()
  }, [incident?.incident_id])

  async function load() {
    try {
      const [det, floor, cams] = await Promise.all([
        getIncident(incident.incident_id),
        incident.floor_id ? getFloorMap(incident.floor_id) : null,
        incident.floor_id ? getFloorCameras(incident.floor_id) : [],
      ])
      setDetail(det)
      setDispatches(det.dispatches || [])
      setFloor(floor)
      setCameras(cams || [])
    } catch (e) {
      console.error('[ARIA] Load incident detail failed:', e)
    } finally {
      setLoading(false)
    }
  }

  async function handleResolve() {
    if (!window.confirm('Mark this incident as resolved?')) return
    setResolving(true)
    try {
      await resolveIncident(incident.incident_id)
      onResolved?.(incident.incident_id)
    } catch (e) {
      console.error('[ARIA] Resolve failed:', e)
    } finally {
      setResolving(false)
    }
  }

  function handleAcked(dispatchId) {
    setDispatches(prev =>
      prev.map(d => d.id === dispatchId ? { ...d, ack_status: 'ACCEPTED' } : d)
    )
  }

  if (!incident) return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100%', color: T.textDim, fontSize: 12,
      fontFamily: T.mono, letterSpacing: 1,
    }}>
      SELECT AN INCIDENT
    </div>
  )

  const sevLabel = SEV_LABEL[incident.severity] || 'MEDIUM'
  const colors   = SEV_COLOR[sevLabel] || SEV_COLOR.MEDIUM

  // Use live data from WebSocket if available, else fall back to DB data
  const blockedNodes = liveBlockedNodes?.length
    ? liveBlockedNodes
    : (detail?.alerts?.[0]?.blocked_nodes || [])

  const pathUpdate = livePathUpdate?.length
    ? livePathUpdate
    : []

  return (
    <div style={{
      height: '100%', overflowY: 'auto',
      padding: '0 0 40px',
      fontFamily: T.sans,
    }}>

      {/* Header */}
      <div style={{
        padding: '16px 20px',
        background: colors.bg,
        borderBottom: `1px solid ${colors.border}`,
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 18 }}>{THREAT_ICON[incident.type] || '⚠'}</span>
              <span style={{ fontSize: 15, fontWeight: 600, color: colors.text }}>
                {THREAT_LABEL[incident.type] || incident.type}
              </span>
              <span style={{
                fontSize: 10, background: colors.badge, color: '#fff',
                padding: '2px 7px', borderRadius: 99, fontWeight: 700,
              }}>
                {sevLabel}
              </span>
            </div>
            <div style={{ fontSize: 12, color: colors.text, opacity: 0.8 }}>
              {incident.full_location}
            </div>
          </div>

          <button
            onClick={handleResolve}
            disabled={resolving}
            style={{
              padding: '7px 16px',
              border: '0.5px solid rgba(34,197,94,0.4)',
              borderRadius: 6,
              background: 'rgba(34,197,94,0.1)',
              color: '#86efac',
              fontSize: 11,
              fontFamily: T.mono,
              cursor: resolving ? 'wait' : 'pointer',
              letterSpacing: 1,
              flexShrink: 0,
            }}
          >
            {resolving ? 'RESOLVING...' : 'RESOLVE'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 20, color: T.textDim, fontSize: 12, fontFamily: T.mono }}>
          LOADING...
        </div>
      ) : (
        <>
          {/* Suggested actions */}
          {incident.suggested_actions?.length > 0 && (
            <Section title="SUGGESTED ACTIONS">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {incident.suggested_actions.map((a, i) => (
                  <div key={i} style={{
                    display: 'flex', gap: 10, alignItems: 'flex-start',
                    fontSize: 12, color: T.textSub,
                  }}>
                    <span style={{
                      minWidth: 20, height: 20, borderRadius: '50%',
                      background: 'rgba(59,130,246,0.12)',
                      border: '0.5px solid rgba(59,130,246,0.25)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 10, color: '#93c5fd', flexShrink: 0,
                      fontFamily: T.mono,
                    }}>
                      {i + 1}
                    </span>
                    {a}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Floor map */}
          {floorData && (
            <Section title={`FLOOR ${floorData.level} MAP — ${incident.full_location}`}>
              <Floor3DMap
                incidentData={{
                  static_grid: floorData.static_grid,
                  grid_width: floorData.static_grid[0]?.length || 0,
                  grid_height: floorData.static_grid.length,
                  all_pois: floorData.pois,
                  blocked_nodes: blockedNodes,
                  path_update: pathUpdate,
                  origin_poi_id: incident.origin_poi_id,
                }}
              />
            </Section>
          )}

          {/* Stats row */}
          <Section title="INCIDENT DETAILS">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                ['Source',    incident.source === 'chat' ? 'Guest report' : 'CCTV camera'],
                ['Detected',  new Date(incident.detected_at).toLocaleTimeString()],
                ['Status',    incident.status?.toUpperCase()],
                ['Dispatches', dispatches.length],
              ].map(([label, val]) => (
                <div key={label} style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: 8, padding: '12px',
                }}>
                  <div style={{ fontSize: 10, color: T.textDim, marginBottom: 4,
                    fontFamily: T.mono, letterSpacing: .5, fontWeight: 600 }}>{label.toUpperCase()}</div>
                  <div style={{ fontSize: 14, color: T.text, fontWeight: 500 }}>{val}</div>
                </div>
              ))}
            </div>
          </Section>

          {/* Dispatch log */}
          <Section title="DISPATCH LOG">
            <DispatchLog
              incidentId = {incident.incident_id}
              dispatches = {dispatches}
              onAcked    = {handleAcked}
            />
          </Section>
        </>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ padding: '24px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
      <div style={{
        fontSize: 10, fontFamily: T.mono, letterSpacing: 2,
        color: '#64748b', marginBottom: 16, fontWeight: 700,
      }}>
        {title}
      </div>
      {children}
    </div>
  )
}