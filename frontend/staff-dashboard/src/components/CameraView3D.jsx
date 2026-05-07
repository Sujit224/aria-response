/**
 * CameraView3D.jsx
 * ─────────────────
 * 3-D floor & camera coverage visualiser for the Staff Dashboard.
 *
 * Shows:
 *  • Full floor grid as raised tiles (rooms = blue, walls = dark, exits = green)
 *  • Camera position as a glowing cylinder + pulsing ring
 *  • Translucent coverage cone spreading from the camera
 *  • Alert overlay (red pulse) when an active incident exists
 *  • Orbit controls – drag to rotate, scroll to zoom, right-drag to pan
 *
 * Props:
 *   floorId   — Firestore floor ID whose grid to render
 *   cameras   — [{id, coord_x, coord_y, name, stream_url}]  (from /map/cameras/:floor_id)
 *   incident  — active incident object (null if none)
 */

import { Suspense, useEffect, useRef, useState, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Environment } from '@react-three/drei'
import * as THREE from 'three'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/* ─── tile colour by grid cell value ─── */
const TILE_COLOR = {
  0: '#0c1a2e',     // wall
  1: '#1e3a5f',     // walkable
  2: '#0d3320',     // safe exit
  3: '#1a1a2e',     // blocked
}
const TILE_HEIGHT = {
  0: 0.08,
  1: 0.04,
  2: 0.06,
  3: 0.04,
}

function Tile({ x, z, type, highlighted, inVision }) {
  const [hov, setHov] = useState(false)
  let col = highlighted ? '#dc2626' : hov ? '#3b82f6' : TILE_COLOR[type] || '#1e3a5f'
  let emissive = highlighted ? '#9b1c1c' : hov ? '#1d4ed8' : col
  let emissiveIntensity = highlighted ? 0.6 : hov ? 0.3 : 0.1
  
  // Highlight vision cells with a subtle cyan glow if not a wall or blocked
  if (inVision && !highlighted && type !== 0) {
    col = '#0284c7'
    emissive = '#38bdf8'
    emissiveIntensity = 0.4
  }

  const height = TILE_HEIGHT[type] || 0.04
  return (
    <mesh
      position={[x, height / 2, z]}
      onPointerEnter={() => setHov(true)}
      onPointerLeave={() => setHov(false)}
    >
      <boxGeometry args={[0.92, height, 0.92]} />
      <meshStandardMaterial
        color={col}
        emissive={emissive}
        emissiveIntensity={emissiveIntensity}
        roughness={0.6}
        metalness={0.3}
      />
    </mesh>
  )
}

/* ─── Helper to check if a grid cell is in camera FOV ─── */
function isInFOV(r, c, cams) {
  for (let cam of cams) {
    const dx = c - cam.gx
    const dz = r - cam.gz
    const dist = Math.sqrt(dx * dx + dz * dz)
    if (dist > 0 && dist <= cam.range) {
      const angle = Math.atan2(dz, dx)
      let diff = Math.abs(angle - cam.facing)
      while (diff > Math.PI) diff -= 2 * Math.PI
      diff = Math.abs(diff)
      if (diff <= cam.fov / 2) return true
    } else if (dist === 0) {
      return true
    }
  }
  return false
}

/* ─── Floor grid from static_grid 2D array ─── */
function FloorGrid({ grid, blockedNodes = [], cams = [], offsetX, offsetZ }) {
  if (!grid || !grid.length) return null
  const rows = grid.length
  const cols = grid[0].length
  const blocked = new Set(blockedNodes.map(([r,c]) => `${r},${c}`))

  return (
    <group>
      {grid.map((row, r) =>
        row.map((cell, c) => {
          const worldX = c + offsetX + 0.5
          const worldZ = r + offsetZ + 0.5
          const isBlocked = blocked.has(`${r},${c}`)
          const inVision = isInFOV(r, c, cams)
          return (
            <Tile
              key={`${r}-${c}`}
              x={worldX}
              z={worldZ}
              type={isBlocked ? 3 : cell}
              highlighted={isBlocked}
              inVision={inVision}
            />
          )
        })
      )}

      {/* Grid border glow */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(cols, 0.01, rows)]} />
        <lineBasicMaterial color="#1e40af" linewidth={1} />
      </lineSegments>
    </group>
  )
}

/* ─── POI Marker ─── */
function POIMarker({ x, z, type, name }) {
  const isRoom = type === 'room'
  const col = isRoom ? '#3b82f6' : type === 'exit' ? '#10b981' : '#f59e0b'
  
  return (
    <group position={[x, 0.05, z]}>
      {isRoom ? (
        <mesh position={[0, 0.4, 0]}>
          <boxGeometry args={[0.7, 0.8, 0.7]} />
          <meshStandardMaterial color={col} transparent opacity={0.15} emissive={col} emissiveIntensity={0.2} />
          <lineSegments>
            <edgesGeometry args={[new THREE.BoxGeometry(0.7, 0.8, 0.7)]} />
            <lineBasicMaterial color={col} transparent opacity={0.4} />
          </lineSegments>
        </mesh>
      ) : (
        <mesh position={[0, 0.2, 0]}>
          <sphereGeometry args={[0.2, 16, 16]} />
          <meshStandardMaterial color={col} emissive={col} emissiveIntensity={0.5} />
        </mesh>
      )}
      <Text
        position={[0, isRoom ? 1.0 : 0.6, 0]}
        fontSize={0.22}
        color="#fff"
        anchorX="center"
        anchorY="bottom"
        outlineWidth={0.02}
        outlineColor="#000"
      >
        {name}
      </Text>
    </group>
  )
}

/* ─── Pulsing camera marker ─── */
function CameraMarker({ x, z, name, hasAlert, facing }) {
  const ringRef   = useRef()
  const coneRef   = useRef()
  const lightRef  = useRef()
  const [ t, setT ] = useState(0)

  useFrame((_, delta) => {
    setT(p => p + delta)
    if (ringRef.current) {
      ringRef.current.scale.setScalar(1 + 0.25 * Math.sin(t * 2.5))
      ringRef.current.material.opacity = 0.5 + 0.5 * Math.sin(t * 2.5)
    }
    if (lightRef.current) {
      lightRef.current.intensity = hasAlert
        ? 2 + 2 * Math.sin(t * 6)
        : 1.2 + 0.4 * Math.sin(t * 1.5)
    }
  })

  const camColor   = hasAlert ? '#ef4444' : '#22d3ee'
  const coneColor  = hasAlert ? 'rgba(239,68,68,0.12)' : 'rgba(34,211,238,0.08)'

  return (
    <group position={[x, 0, z]}>
      {/* Camera body */}
      <mesh position={[0, 0.35, 0]}>
        <cylinderGeometry args={[0.18, 0.18, 0.5, 16]} />
        <meshStandardMaterial
          color={camColor}
          emissive={camColor}
          emissiveIntensity={hasAlert ? 2 : 1}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>

      {/* Pulsing ring */}
      <mesh ref={ringRef} position={[0, 0.06, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.28, 0.38, 32]} />
        <meshBasicMaterial color={camColor} transparent side={THREE.DoubleSide} />
      </mesh>

      {/* Point light */}
      <pointLight
        ref={lightRef}
        color={camColor}
        intensity={1.5}
        distance={6}
        decay={2}
      />

      {/* Coverage cone (translucent), angled towards facing direction */}
      <group rotation={[0, -facing, 0]}>
        <mesh ref={coneRef} position={[2.5, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[3, 5, 32, 1, true]} />
          <meshBasicMaterial
            color={camColor}
            transparent
            opacity={hasAlert ? 0.15 : 0.07}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      </group>

      {/* Camera label */}
      <Text
        position={[0, 0.9, 0]}
        fontSize={0.35}
        color={camColor}
        anchorX="center"
        anchorY="bottom"
        outlineWidth={0.02}
        outlineColor="#000"
      >
        {name || 'CAM'}
      </Text>
    </group>
  )
}

/* ─── Alert flame particle overlay ─── */
function AlertRing({ active }) {
  const ref = useRef()
  useFrame((_, d) => {
    if (ref.current && active) {
      ref.current.rotation.y += d * 1.2
      ref.current.children.forEach((c, i) => {
        c.material.opacity = 0.3 + 0.4 * Math.sin(Date.now() * 0.003 + i)
      })
    }
  })
  if (!active) return null
  return (
    <group ref={ref}>
      {[0, 1, 2, 3, 4, 5].map(i => (
        <mesh
          key={i}
          position={[
            Math.cos((i / 6) * Math.PI * 2) * 5,
            0.3,
            Math.sin((i / 6) * Math.PI * 2) * 5,
          ]}
        >
          <sphereGeometry args={[0.25, 8, 8]} />
          <meshBasicMaterial color="#ef4444" transparent opacity={0.5} />
        </mesh>
      ))}
    </group>
  )
}

/* ─── Scene (everything inside Canvas) ─── */
function Scene({ floorData, cameras, incident }) {
  const grid = useMemo(() => {
    let g = floorData?.static_grid || []
    if (typeof g === 'string') {
      try { g = JSON.parse(g) } catch(e) { g = [] }
    }
    return Array.isArray(g) ? g : []
  }, [floorData?.static_grid])

  const rows    = grid.length
  const cols    = grid[0]?.length || 0
  const blocked = incident?.blocked_nodes || []
  const hasAlert = !!incident
  const all_pois = floorData?.pois || []

  // Map camera grid coords → world coords
  const offsetX = -cols / 2
  const offsetZ = -rows / 2

  // Pre-calculate camera data for FOV highlighting
  const processedCams = useMemo(() => {
    return cameras.map(cam => {
      const gx = cam.coord_x ?? Math.floor(cols / 2)
      const gz = cam.coord_y ?? Math.floor(rows / 2)
      // Make them face towards the center of the room for demo purposes
      const facing = Math.atan2((rows/2) - gz, (cols/2) - gx)
      return {
        id: cam.id,
        name: cam.name || cam.id?.slice(0, 8),
        gx,
        gz,
        worldX: gx + offsetX + 0.5,
        worldZ: gz + offsetZ + 0.5,
        facing,
        fov: Math.PI / 2.5, // 72 degrees
        range: 7, // tiles
      }
    })
  }, [cameras, cols, rows, offsetX, offsetZ])

  return (
    <>
      {/* Ambient + directional light */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 20, 10]} intensity={0.8} castShadow />
      <directionalLight position={[-10, 10, -10]} intensity={0.3} color="#3b82f6" />

      {/* Floor */}
      <FloorGrid
        grid={grid}
        blockedNodes={blocked}
        cams={processedCams}
        offsetX={offsetX}
        offsetZ={offsetZ}
      />

      {/* POI Markers (Rooms, Exits) */}
      {all_pois.map(poi => (
        <POIMarker
          key={poi.id}
          x={poi.coord_x + offsetX + 0.5}
          z={poi.coord_y + offsetZ + 0.5}
          type={poi.type}
          name={poi.name}
        />
      ))}

      {/* Camera markers */}
      {processedCams.map(cam => (
        <CameraMarker
          key={cam.id}
          x={cam.worldX}
          z={cam.worldZ}
          name={cam.name}
          hasAlert={hasAlert}
          facing={cam.facing}
        />
      ))}

      {/* Alert overlay */}
      <AlertRing active={hasAlert} />

      {/* Floor label */}
      <Text
        position={[0, 0.15, -(rows / 2) - 1.5]}
        fontSize={0.6}
        color={hasAlert ? '#ef4444' : '#3b82f6'}
        anchorX="center"
        outlineWidth={0.04}
        outlineColor="#000"
      >
        {`FLOOR ${floorData?.level ?? '?'}  ·  ${cols}×${rows} GRID`}
      </Text>

      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        minDistance={4}
        maxDistance={60}
        minPolarAngle={0.1}
        maxPolarAngle={Math.PI / 2}
      />
    </>
  )
}

/* ─── Loading spinner inside canvas ─── */
function CanvasLoader() {
  return (
    <mesh>
      <torusGeometry args={[1, 0.1, 8, 32]} />
      <meshBasicMaterial color="#3b82f6" wireframe />
    </mesh>
  )
}

/* ─── Main exported component ─── */
export function CameraView3D({ floorId, incident }) {
  const [floorData, setFloorData] = useState(null)
  const [cameras,   setCameras]   = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)

  useEffect(() => {
    if (!floorId) return
    setLoading(true)
    setError(null)

    Promise.all([
      fetch(`${API}/map/floor/${floorId}`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/map/cameras/${floorId}`).then(r => r.ok ? r.json() : []),
    ])
      .then(([floor, cams]) => {
        setFloorData(floor)
        setCameras(Array.isArray(cams) ? cams : [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [floorId])

  if (!floorId) return (
    <div style={styles.empty}>SELECT A FLOOR TO VIEW 3D MAP</div>
  )
  if (loading) return (
    <div style={styles.empty}>LOADING FLOOR DATA...</div>
  )
  if (error || !floorData) return (
    <div style={styles.empty}>FLOOR DATA UNAVAILABLE</div>
  )

  const hasAlert = !!incident

  return (
    <div style={{ ...styles.wrapper, border: `1px solid ${hasAlert ? '#dc2626' : '#1e3a5f'}` }}>
      {/* Header */}
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: hasAlert ? '#ef4444' : '#22d3ee',
            boxShadow: `0 0 8px ${hasAlert ? '#ef4444' : '#22d3ee'}`,
            animation: 'pulse-dot 1.2s ease-in-out infinite',
          }} />
          <span style={{ fontSize: 11, fontFamily: 'monospace', letterSpacing: 2, color: hasAlert ? '#ef4444' : '#22d3ee' }}>
            {hasAlert ? 'ALERT — CAMERA COVERAGE VIEW' : 'CAMERA COVERAGE — 3D VIEW'}
          </span>
        </div>
        <span style={{ fontSize: 10, color: '#475569', fontFamily: 'monospace' }}>
          {cameras.length} CAMERA{cameras.length !== 1 ? 'S' : ''} · FLOOR {floorData.level}
        </span>
      </div>

      {/* Canvas */}
      <Canvas
        shadows
        camera={{ position: [0, 18, 20], fov: 45, near: 0.1, far: 200 }}
        style={{ background: 'radial-gradient(ellipse at center, #050d1a 0%, #020810 100%)' }}
        gl={{ antialias: true, alpha: false }}
      >
        <Suspense fallback={<CanvasLoader />}>
          <Scene
            floorData={floorData}
            cameras={cameras}
            incident={incident}
          />
        </Suspense>
      </Canvas>

      {/* Legend */}
      <div style={styles.legend}>
        {[
          { col: '#1e3a5f', label: 'WALKABLE' },
          { col: '#0284c7', label: 'FOV' },
          { col: '#0c1a2e', label: 'WALL' },
          { col: '#0d3320', label: 'EXIT' },
          { col: '#dc2626', label: 'BLOCKED' },
          { col: '#22d3ee', label: 'CAMERA' },
        ].map(({ col, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: col }} />
            <span style={{ fontSize: 9, color: '#475569', fontFamily: 'monospace' }}>{label}</span>
          </div>
        ))}
      </div>

      <style>{`@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.3} }`}</style>
    </div>
  )
}

const styles = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    borderRadius: 12,
    overflow: 'hidden',
    background: '#020810',
    transition: 'border-color 0.3s',
  },
  header: {
    padding: '10px 16px',
    background: 'rgba(5,13,26,0.9)',
    borderBottom: '1px solid #0f2035',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
  },
  legend: {
    display: 'flex',
    gap: 16,
    padding: '8px 16px',
    background: 'rgba(5,13,26,0.9)',
    borderTop: '1px solid #0f2035',
    flexShrink: 0,
  },
  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#1e3a5f',
    fontSize: 12,
    fontFamily: 'monospace',
    letterSpacing: 2,
    background: '#020810',
    borderRadius: 12,
    border: '1px solid #0f2035',
  },
}
