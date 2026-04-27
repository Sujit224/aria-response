import { useEffect, useRef } from 'react'
import { updateStaffLocation } from '../lib/api'

const INTERVAL_MS = 30_000

/**
 * Sends a staff location heartbeat every 30 seconds.
 * staffId, floorId, blockId come from the staff's login context.
 */
export function useLocationHeartbeat({ staffId, floorId, blockId }) {
  const timerRef = useRef(null)

  useEffect(() => {
    if (!staffId || !floorId || !blockId) return

    const ping = async () => {
      try {
        await updateStaffLocation(staffId, floorId, blockId)
      } catch (e) {
        console.warn('[ARIA] Location heartbeat failed:', e.message)
      }
    }

    ping()                                          // immediate first ping
    timerRef.current = setInterval(ping, INTERVAL_MS)

    return () => clearInterval(timerRef.current)
  }, [staffId, floorId, blockId])
}