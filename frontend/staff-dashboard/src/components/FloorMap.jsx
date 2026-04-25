import { useEffect, useRef } from 'react'

const CELL  = 22        // px per grid cell
const COLORS = {
  wall:     '#060d18',
  walkable: '#0a1828',
  corridor: '#0d2035',
  room:     '#0f2540',
  exit:     '#052e16',
  medical:  '#1a2040',
  blocked:  'rgba(220,38,38,0.55)',
  path:     'rgba(34,197,94,0.7)',
  origin:   '#3b82f6',
  exitDot:  '#22c55e',
}

/**
 * Props:
 *   grid         — static_grid 2D array from /map/floor/{id}
 *   pois         — array of {coord_x, coord_y, name, type, is_safe_exit}
 *   blockedNodes — [[x,y],...] red hazard cells from EmergencyAlert
 *   pathUpdate   — [[x,y],...] green A* path from THREAT_DETECTED / PATH_UPDATE
 *   originCoord  — {x,y} guest's room position (blue dot)
 *   cameras      — array of {coord_x, coord_y, zone_name} (optional FOV boxes)
 *   width        — container width override (default auto)
 */
export function FloorMap({
  grid = [],
  pois = [],
  blockedNodes = [],
  pathUpdate = [],
  originCoord = null,
  cameras = [],
  width,
}) {
  const canvasRef = useRef(null)

  const rows = grid.length
  const cols = grid[0]?.length || 0

  // Build lookup sets for fast rendering
  const blockedSet = new Set(blockedNodes.map(([x, y]) => `${x},${y}`))
  const pathSet    = new Set(pathUpdate.map(([x, y]) => `${x},${y}`))

  const poiByCoord = {}
  pois.forEach(p => { poiByCoord[`${p.coord_x},${p.coord_y}`] = p })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !grid.length) return
    const ctx = canvas.getContext('2d')
    const W = cols * CELL
    const H = rows * CELL

    canvas.width  = W
    canvas.height = H

    ctx.clearRect(0, 0, W, H)

    // ── Draw cells ──────────────────────────────────────────────
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const key = `${x},${y}`
        const isWall    = grid[y][x] === 1
        const isBlocked = blockedSet.has(key)
        const isPath    = pathSet.has(key)
        const poi       = poiByCoord[key]

        // Base cell color
        let fill = isWall ? COLORS.wall : COLORS.walkable
        if (!isWall && poi) {
          if (poi.is_safe_exit)        fill = COLORS.exit
          else if (poi.type === 'medical') fill = COLORS.medical
          else if (poi.type === 'room')    fill = COLORS.room
        }

        ctx.fillStyle = fill
        ctx.fillRect(x * CELL, y * CELL, CELL, CELL)

        // Grid line
        ctx.strokeStyle = 'rgba(59,130,246,0.08)'
        ctx.lineWidth   = 0.5
        ctx.strokeRect(x * CELL, y * CELL, CELL, CELL)

        // Hazard overlay (red)
        if (isBlocked && !isWall) {
          ctx.fillStyle = COLORS.blocked
          ctx.fillRect(x * CELL, y * CELL, CELL, CELL)
          // Pulse ring
          ctx.strokeStyle = 'rgba(220,38,38,0.8)'
          ctx.lineWidth   = 1
          ctx.strokeRect(x * CELL + 1, y * CELL + 1, CELL - 2, CELL - 2)
        }

        // Path overlay (green)
        if (isPath && !isWall) {
          ctx.fillStyle = COLORS.path
          ctx.fillRect(x * CELL + 3, y * CELL + 3, CELL - 6, CELL - 6)
        }
      }
    }

    // ── Camera FOV boxes ────────────────────────────────────────
    cameras.forEach(cam => {
      if (!cam.coverage_zones) return
      cam.coverage_zones.forEach(zone => {
        const zx = zone.start_x * CELL
        const zy = zone.start_y * CELL
        const zw = (zone.end_x - zone.start_x) * CELL
        const zh = (zone.end_y - zone.start_y) * CELL
        ctx.fillStyle   = 'rgba(251,146,60,0.06)'
        ctx.fillRect(zx, zy, zw, zh)
        ctx.strokeStyle = 'rgba(251,146,60,0.4)'
        ctx.lineWidth   = 1
        ctx.strokeRect(zx, zy, zw, zh)
      })
    })

    // ── POI labels ──────────────────────────────────────────────
    ctx.font      = `bold ${CELL * 0.38}px monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    pois.forEach(p => {
      const cx = p.coord_x * CELL + CELL / 2
      const cy = p.coord_y * CELL + CELL / 2

      if (p.is_safe_exit) {
        // Green exit dot
        ctx.beginPath()
        ctx.arc(cx, cy, CELL * 0.3, 0, Math.PI * 2)
        ctx.fillStyle = COLORS.exitDot
        ctx.fill()
        ctx.fillStyle = '#fff'
        ctx.font      = `bold ${CELL * 0.42}px monospace`
        ctx.fillText('E', cx, cy)
      } else if (p.type === 'medical') {
        ctx.fillStyle = '#60a5fa'
        ctx.fillText('✚', cx, cy)
      } else if (p.type === 'room') {
        ctx.fillStyle = 'rgba(148,163,184,0.7)'
        ctx.font      = `${CELL * 0.32}px monospace`
        const shortName = p.name.replace('Room ', '')
        ctx.fillText(shortName, cx, cy)
      }
    })

    // ── Origin dot (guest position — blue) ──────────────────────
    if (originCoord) {
      const ox = originCoord.x * CELL + CELL / 2
      const oy = originCoord.y * CELL + CELL / 2
      ctx.beginPath()
      ctx.arc(ox, oy, CELL * 0.38, 0, Math.PI * 2)
      ctx.fillStyle   = COLORS.origin
      ctx.fill()
      ctx.strokeStyle = '#bfdbfe'
      ctx.lineWidth   = 1.5
      ctx.stroke()
    }

    // ── Path start / end markers ─────────────────────────────────
    if (pathUpdate.length >= 2) {
      const [sx, sy] = pathUpdate[0]
      const [ex, ey] = pathUpdate[pathUpdate.length - 1]

      // Start
      ctx.beginPath()
      ctx.arc(sx * CELL + CELL / 2, sy * CELL + CELL / 2, CELL * 0.3, 0, Math.PI * 2)
      ctx.fillStyle = '#22c55e'
      ctx.fill()

      // End (exit)
      ctx.beginPath()
      ctx.arc(ex * CELL + CELL / 2, ey * CELL + CELL / 2, CELL * 0.3, 0, Math.PI * 2)
      ctx.fillStyle = '#86efac'
      ctx.fill()
    }

  }, [grid, pois, blockedNodes, pathUpdate, originCoord, cameras])

  if (!grid.length) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 200, color: '#475569', fontSize: 12,
        fontFamily: 'monospace', letterSpacing: 1,
      }}>
        NO FLOOR DATA
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto', overflowY: 'auto', width: width || '100%' }}>
      <canvas
        ref={canvasRef}
        style={{ display: 'block', imageRendering: 'pixelated' }}
      />
      {/* Legend */}
      <div style={{
        display: 'flex', gap: 16, padding: '8px 4px',
        flexWrap: 'wrap',
      }}>
        {[
          { color: COLORS.path,    label: 'Evacuation route' },
          { color: COLORS.blocked, label: 'Hazard zone' },
          { color: COLORS.exit,    label: 'Safe exit' },
          { color: COLORS.medical, label: 'Aid kit' },
          { color: COLORS.origin,  label: 'Guest position' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
            <span style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}