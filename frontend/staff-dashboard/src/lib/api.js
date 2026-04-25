const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

async function req(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

// ── Incidents ─────────────────────────────────────────
export const getActiveIncidents = (hotelId) =>
  req(`/incidents/active?hotel_id=${hotelId}`)

export const getIncident = (incidentId) =>
  req(`/incidents/${incidentId}`)

export const resolveIncident = (incidentId) =>
  req(`/incidents/${incidentId}/resolve`, { method: 'POST' })

export const ackDispatch = (incidentId, dispatchId) =>
  req(`/incidents/${incidentId}/ack?dispatch_id=${dispatchId}`, { method: 'PATCH' })

export const rerouteGuest = (incidentId, guestSessionId) =>
  req(`/incidents/${incidentId}/reroute?guest_session_id=${guestSessionId}`, { method: 'POST' })

// ── Map / floor data ──────────────────────────────────
export const getFloorMap = (floorId) =>
  req(`/map/floor/${floorId}`)

export const getFloorCameras = (floorId) =>
  req(`/map/cameras/${floorId}`)

export const getHotelBlocks = (hotelId) =>
  req(`/map/blocks/${hotelId}`)

// ── Staff ─────────────────────────────────────────────
export const getOnDutyStaff = (hotelId) =>
  req(`/staff/on-duty?hotel_id=${hotelId}`)

export const getPendingDispatches = (hotelId) =>
  req(`/staff/dispatches/pending?hotel_id=${hotelId}`)

export const updateStaffLocation = (staffId, floorId, blockId) =>
  req(`/staff/${staffId}/location`, {
    method: 'PATCH',
    body: JSON.stringify({ floor_id: floorId, block_id: blockId }),
  })