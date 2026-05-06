import { useState, useEffect, useCallback } from 'react'
import { TopBar } from '../components/TopBar'
import { IncidentCard } from '../components/IncidentCard'
import { IncidentDetail } from '../components/IncidentDetail'
import { Hotel3D } from '../components/Hotel3D'
import Building3D from '../components/Building3D'
import { useStaffSocket } from '../hooks/useStaffSocket'
import { useLocationHeartbeat } from '../hooks/useLocationHeartbeat'
import { getActiveIncidents, getHotelBlocks } from '../lib/api'
import { SEV_LABEL, T } from '../lib/constants'

// Read from env or URL params
const VENUE_ID = import.meta.env.VITE_VENUE_ID || new URLSearchParams(location.search).get('venue') || ''
const STAFF_ID = import.meta.env.VITE_STAFF_ID || new URLSearchParams(location.search).get('staff') || 'demo'
const FLOOR_ID = new URLSearchParams(location.search).get('floor') || ''
const BLOCK_ID = new URLSearchParams(location.search).get('block') || ''

export function Dashboard({ onGoQR }) {
  const [incidents,  setIncidents]  = useState([])
  const [blocks,     setBlocks]     = useState([])
  const [selected,   setSelected]   = useState(null)
  const [selectedFloorId, setSelectedFloorId] = useState(null)
  const [liveBlocked, setLiveBlocked] = useState([])
  const [livePath,    setLivePath]    = useState([])
  const [wsStatus,    setWsStatus]    = useState('connecting')
  const [loading,     setLoading]     = useState(true)

  // Staff location heartbeat
  useLocationHeartbeat({ staffId: STAFF_ID, floorId: FLOOR_ID, blockId: BLOCK_ID })

  // Load active incidents on mount
  useEffect(() => {
    if (!VENUE_ID) return
    fetchIncidents()
    fetchBlocks()
    const t = setInterval(fetchIncidents, 30_000)  // poll every 30s as fallback
    return () => clearInterval(t)
  }, [])

  async function fetchBlocks() {
    try {
      const data = await getHotelBlocks(VENUE_ID)
      setBlocks(data)
    } catch (e) {
      console.error('[ARIA] Fetch blocks failed:', e)
    }
  }

  async function fetchIncidents() {
    try {
      const data = await getActiveIncidents(VENUE_ID)
      // Normalize 'id' to 'incident_id' for consistency with WebSocket events
      setIncidents(data.map(i => ({ ...i, incident_id: i.incident_id || i.id })))
    } catch (e) {
      console.error('[ARIA] Fetch incidents failed:', e)
    } finally {
      setLoading(false)
    }
  }

  // WebSocket handlers
  const onThreatDetected = useCallback((data) => {
    // Add or update incident in the live list
    setIncidents(prev => {
      const exists = prev.find(i => i.incident_id === data.incident_id)
      if (exists) {
        return prev.map(i =>
          i.incident_id === data.incident_id
            ? { ...i, blocked_nodes: data.blocked_nodes }
            : i
        )
      }
      return [{
        incident_id:    data.incident_id,
        type:           data.type.toLowerCase(),
        severity:       data.severity === 'CRITICAL' ? 5 : data.severity === 'HIGH' ? 4 : 3,
        full_location:  data.full_location,
        source:         'vision',
        status:         'active',
        detected_at:    new Date().toISOString(),
        blocked_nodes:  data.blocked_nodes,
        dispatches:     [],
      }, ...prev]
    })

    // If this incident is currently selected, update live overlays
    if (selected?.incident_id === data.incident_id) {
      setLiveBlocked(data.blocked_nodes || [])
      setLivePath(data.path_update || [])
    }

    // Auto-select if CRITICAL and nothing selected
    setSelected(prev => {
      if (!prev && data.severity === 'CRITICAL') {
        return { incident_id: data.incident_id, type: data.type.toLowerCase(),
          severity: 5, full_location: data.full_location, source: 'vision',
          status: 'active', detected_at: new Date().toISOString() }
      }
      return prev
    })
  }, [selected])

  const onStaffAlert = useCallback((data) => {
    // Update dispatch list for the affected incident
    setIncidents(prev =>
      prev.map(i =>
        i.incident_id === data.incident_id
          ? { ...i, _staffAlert: data }
          : i
      )
    )
  }, [])

  const onIncidentResolved = useCallback((data) => {
    setIncidents(prev => prev.filter(i => i.incident_id !== data.incident_id))
    setSelected(prev => prev?.incident_id === data.incident_id ? null : prev)
  }, [])

  const onPathUpdate = useCallback((data) => {
    if (selected?.incident_id === data.incident_id) {
      setLivePath(data.path_update || [])
      setLiveBlocked(data.blocked_nodes || [])
    }
  }, [selected])

  const { status } = useStaffSocket({
    venueId:          VENUE_ID,
    staffId:          STAFF_ID,
    onThreatDetected,
    onStaffAlert,
    onIncidentResolved,
    onPathUpdate,
  })

  useEffect(() => { setWsStatus(status) }, [status])

  function handleSelect(incident) {
    setSelected(incident)
    setSelectedFloorId(incident.floor_id)
    setLiveBlocked([])
    setLivePath([])
  }

  function handleFloorSelect(floorId) {
    // If there is an incident on this floor, select it
    const inc = incidents.find(i => i.floor_id === floorId)
    if (inc) {
      handleSelect(inc)
    } else {
      setSelected(null)
      setSelectedFloorId(floorId)
    }
  }

  function handleResolved(incidentId) {
    setIncidents(prev => prev.filter(i => i.incident_id !== incidentId))
    setSelected(null)
  }

  const criticalCount = incidents.filter(i => SEV_LABEL[i.severity] === 'CRITICAL').length

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', background: T.bg,
      color: T.text, fontFamily: T.sans,
      overflow: 'hidden',
    }}>
      <TopBar
        wsStatus      = {wsStatus}
        activeCount   = {incidents.length}
        criticalCount = {criticalCount}
        onGoQR        = {onGoQR}
      />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ── Left panel: incident list ──────────────────────── */}
        <div style={{
          width: 320,
          background: T.bgCard,
          borderRight: `1px solid ${T.border}`,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          flexShrink: 0,
          zIndex: 10,
        }}>
          <div style={{
            padding: '16px 20px 12px',
            borderBottom: `1px solid ${T.border}`,
            background: 'rgba(15, 23, 42, 0.8)',
            backdropFilter: 'blur(8px)'
          }}>
            <div style={{
              fontSize: 11, letterSpacing: 2, color: T.textDim,
              fontFamily: T.sans, fontWeight: 700,
            }}>
              ACTIVE INCIDENTS
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
            {loading ? (
              <div style={{ fontSize: 12, color: T.textDim, fontFamily: T.mono,
                padding: '20px 0', textAlign: 'center' }}>
                LOADING...
              </div>
            ) : incidents.length === 0 ? (
              <div style={{ fontSize: 12, color: T.textDim, fontFamily: T.mono,
                padding: '40px 0', textAlign: 'center', lineHeight: 2 }}>
                NO ACTIVE INCIDENTS
                <br />
                <span style={{ fontSize: 10, color: T.textDim }}>All clear</span>
              </div>
            ) : (
              incidents.map(inc => (
                <IncidentCard
                  key       = {inc.incident_id}
                  incident  = {inc}
                  selected  = {selected?.incident_id === inc.incident_id}
                  onSelect  = {handleSelect}
                />
              ))
            )}
          </div>

          <Hotel3D
            blocks={blocks}
            incidents={incidents}
            selected={selectedFloorId}
            onSelect={handleFloorSelect}
          />
        </div>

        {/* ── Right panel: incident detail ────────────────────── */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {selected || selectedFloorId ? (
            <IncidentDetail
              incident        = {selected}
              floorId         = {selectedFloorId}
              livePathUpdate  = {livePath}
              liveBlockedNodes = {liveBlocked}
              onResolved      = {handleResolved}
            />
          ) : (
            <Building3D blocks={blocks} incidents={incidents} />
          )}
        </div>
      </div>
    </div>
  )
}