/**
 * session.js — Guest session & identity helpers
 *
 * session_id  : random UUID persisted in localStorage — survives page refresh
 * venue_id    : hotel/venue ID from URL ?venue= param or VITE_VENUE_ID env
 * room_id     : POI id of the guest's room — from URL ?room= param, or
 *               auto-picked from Firestore if none set (for quick testing)
 * phone       : guest phone (stored after check-in) for FCM token linking
 */

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export function getSessionId() {
  let id = localStorage.getItem('aria_session_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('aria_session_id', id)
  }
  return id
}

export function clearSessionId() {
  localStorage.removeItem('aria_session_id')
}

export function getVenueId() {
  return (
    new URLSearchParams(location.search).get('venue') ||
    import.meta.env.VITE_VENUE_ID ||
    ''
  )
}

export function getRoomId() {
  const fromUrl = new URLSearchParams(location.search).get('room')
  if (fromUrl) {
    localStorage.setItem('aria_room_id', fromUrl)
    return fromUrl
  }
  
  const lastVenue = localStorage.getItem('aria_last_venue_id')
  const currentVenue = getVenueId()
  if (lastVenue && lastVenue !== currentVenue) {
    localStorage.setItem('aria_last_venue_id', currentVenue)
    localStorage.removeItem('aria_room_id')
    localStorage.removeItem('aria_room_name')
    return ''
  }
  if (!lastVenue && currentVenue) {
    localStorage.setItem('aria_last_venue_id', currentVenue)
  }

  return localStorage.getItem('aria_room_id') || ''
}

export function setRoomId(id) {
  localStorage.setItem('aria_room_id', id)
}

export function getGuestPhone() {
  return localStorage.getItem('aria_guest_phone') || ''
}

export function setGuestPhone(phone) {
  localStorage.setItem('aria_guest_phone', phone)
}

export function getRoomName() {
  return localStorage.getItem('aria_room_name') || 'Unknown Room'
}

export function setRoomName(name) {
  localStorage.setItem('aria_room_name', name)
}

/**
 * For testing: auto-assigns a random OCCUPIED room from the hotel
 * when no room_id is available via URL or localStorage.
 * Picks a random room from Firestore-backed occupied rooms.
 * Returns the room_id string after storing it in localStorage.
 */
export async function autoAssignTestRoom() {
  const venueId = getVenueId()
  if (!venueId) return ''

  try {
    // Fetch all blocks, then floors, then pick a random occupied room
    // We use the admin map API to list blocks and pick one to look up floors
    const blocksRes = await fetch(`${API}/map/blocks/auto`)
    // Fallback: directly query pois via map API
    const poisRes = await fetch(`${API}/map/pois?type=room&limit=200`)
    if (!poisRes.ok) throw new Error('Cannot fetch rooms')

    const pois = await poisRes.json()
    const rooms = pois.filter(p => p.type === 'room')
    if (!rooms.length) return ''

    // Pick a random room
    const picked = rooms[Math.floor(Math.random() * rooms.length)]
    setRoomId(picked.id)
    setRoomName(picked.name)
    console.log(`[ARIA] Auto-assigned test room: ${picked.name} (${picked.id})`)
    return picked.id
  } catch (e) {
    console.warn('[ARIA] Could not auto-assign room:', e.message)
    return ''
  }
}
