import React, { useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Text, Line, Edges, Float, MeshDistortMaterial, Html } from '@react-three/drei'
import * as THREE from 'three'

// --- 1. Scene Effects & Lighting ---
function SceneEffects() {
  const { scene } = useThree()
  
  useMemo(() => {
    scene.fog = new THREE.FogExp2('#0f172a', 0.015)
  }, [scene])

  return (
    <>
      <ambientLight intensity={1.5} />
      <hemisphereLight intensity={0.5} color="#3b82f6" groundColor="#0f172a" />
      <directionalLight 
        position={[10, 20, 10]} 
        intensity={1.2} 
        castShadow 
        shadow-mapSize={[2048, 2048]}
      >
        <orthographicCamera attach="shadow-camera" args={[-30, 30, 30, -30]} />
      </directionalLight>
      
      {/* Holographic Ground Glow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
        <circleGeometry args={[25, 64]} />
        <meshBasicMaterial color="#1e3a8a" transparent opacity={0.15} />
      </mesh>
      
      <pointLight position={[-10, 10, -10]} intensity={1.5} color="#60a5fa" />
      <pointLight position={[10, 5, -5]} intensity={1.2} color="#a78bfa" />
    </>
  )
}

// --- 2. Advanced Path Rendering ---
function AnimatedPath({ points }) {
  const lineRef = useRef()
  const dashOffset = useRef(0)

  useFrame((state, delta) => {
    if (lineRef.current) {
      dashOffset.current -= delta * 1.5
      lineRef.current.material.dashOffset = dashOffset.current
    }
  })

  return (
    <Line
      ref={lineRef}
      points={points}
      color="#10b981"
      lineWidth={5}
      dashed
      dashSize={0.6}
      dashScale={1}
      gapSize={0.4}
    />
  )
}

// --- 3. Premium Markers ---
function PulsingMarker({ position, color, label, isIncident = false, type = 'poi' }) {
  const meshRef = useRef()
  const ringRef = useRef()
  const lightRef = useRef()
  const beamRef = useRef()

  useFrame((state) => {
    const time = state.clock.getElapsedTime()
    if (meshRef.current) {
      if (type === 'room') {
        meshRef.current.position.y = position[1] + 0.8
      } else {
        meshRef.current.position.y = position[1] + 0.3 + Math.sin(time * 3) * 0.1
        meshRef.current.rotation.y = time * 2
      }
    }
    if (ringRef.current) {
      const s = 1 + (time % 1) * (type === 'room' ? 2 : 1.5)
      ringRef.current.scale.set(s, s, s)
      ringRef.current.material.opacity = Math.max(0, 0.6 - (time % 1))
    }
    if (lightRef.current) {
      lightRef.current.intensity = type === 'room' ? 0.8 : (2 + Math.sin(time * 8) * 1.5)
    }
    if (beamRef.current) {
      beamRef.current.material.opacity = 0.1 + Math.sin(time * 4) * 0.05
    }
  })

  const isCritical = isIncident || type === 'exit' || type === 'stairwell'

  return (
    <group position={position}>
      {/* Glow Point Light */}
      <pointLight ref={lightRef} distance={5} color={color} />

      {/* Critical Data Beam */}
      {isCritical && (
        <mesh ref={beamRef} position={[0, 5, 0]}>
          <cylinderGeometry args={[0.05, 0.2, 10, 8, 1, true]} />
          <meshBasicMaterial color={color} transparent opacity={0.15} blending={THREE.AdditiveBlending} />
        </mesh>
      )}

      {/* Main Geometry */}
      <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
        <mesh ref={meshRef} castShadow>
          {type === 'room' ? (
            <>
              <boxGeometry args={[0.8, 1.6, 0.8]} />
              <meshStandardMaterial 
                color={color} 
                transparent 
                opacity={0.1} 
                metalness={0.9} 
                roughness={0.1}
                emissive={color}
                emissiveIntensity={0.1}
              />
              <Edges color={color} opacity={0.5} transparent />
            </>
          ) : isIncident ? (
            <octahedronGeometry args={[0.3, 0]} />
          ) : type === 'exit' ? (
            <boxGeometry args={[0.4, 0.4, 0.4]} />
          ) : (
            <sphereGeometry args={[0.2, 16, 16]} />
          )}
          {type !== 'room' && (
            <meshStandardMaterial 
              color={color} 
              emissive={color} 
              emissiveIntensity={1.2} 
              metalness={0.8} 
              roughness={0.2} 
            />
          )}
        </mesh>
      </Float>
      
      {/* Pulsing Floor Ring */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.4, 0.5, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.6} />
      </mesh>

      {/* Billboard Label */}
      <Text
        position={[0, type === 'room' ? 2.2 : 1.2, 0]}
        color="white"
        fontSize={0.25}
        maxWidth={2}
        textAlign="center"
        anchorX="center" 
        anchorY="bottom" 
        fontWeight="bold"
        outlineWidth={0.02}
        outlineColor="#000"
      >
        {label}
      </Text>
    </group>
  )
}

// --- 4. Main Grid Model ---
function GridModel({ incidentData }) {
  const {
    static_grid, guest_coord, exit_coord, path_update,
    blocked_nodes, all_pois
  } = incidentData

  const grid_height = incidentData.grid_height || static_grid.length
  const grid_width = incidentData.grid_width || (static_grid[0] ? static_grid[0].length : 0)

  const offsetX = -grid_width / 2
  const offsetZ = -grid_height / 2

  // Optimized wall generation
  const wallGeometries = useMemo(() => {
    let grid = static_grid
    if (typeof grid === 'string') {
      try { grid = JSON.parse(grid) } catch(e) { grid = [] }
    }
    const walls = []
    if (Array.isArray(grid)) {
      for (let y = 0; y < Math.min(grid_height, grid.length); y++) {
        const row = grid[y]
        if (!Array.isArray(row)) continue
        for (let x = 0; x < Math.min(grid_width, row.length); x++) {
          if (row[x] === 1) {
            walls.push({ x: x + offsetX + 0.5, z: y + offsetZ + 0.5 })
          }
        }
      }
    }
    return walls
  }, [static_grid, grid_width, grid_height, offsetX, offsetZ])

  const pathPoints = useMemo(() => {
    if (!Array.isArray(path_update)) return []
    return path_update.map(p => new THREE.Vector3(p[0] + offsetX + 0.5, 0.15, p[1] + offsetZ + 0.5))
  }, [path_update, offsetX, offsetZ])

  // Premium Materials
  const wallMaterial = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#1e293b',
    metalness: 0.9,
    roughness: 0.1,
    transparent: true,
    opacity: 0.6,
    transmission: 0.5,
    thickness: 1,
  }), [])

  const floorMaterial = useMemo(() => new THREE.MeshStandardMaterial({
    color: '#1e293b',
    roughness: 0.1,
    metalness: 0.9,
    emissive: '#0f172a',
    emissiveIntensity: 0.5
  }), [])

  return (
    <group>
      {/* Main Floor Slab with Scanlines */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow material={floorMaterial}>
        <planeGeometry args={[grid_width + 40, grid_height + 40]} />
      </mesh>
      
      {/* Scanline Overlay */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.04, 0]}>
        <planeGeometry args={[grid_width + 40, grid_height + 40]} />
        <meshBasicMaterial color="#3b82f6" transparent opacity={0.05} side={THREE.DoubleSide}>
          <canvasTexture attach="map" args={[(() => {
            const c = document.createElement('canvas')
            c.width = 1
            c.height = 4
            const ctx = c.getContext('2d')
            ctx.fillStyle = 'rgba(255,255,255,1)'
            ctx.fillRect(0,0,1,1)
            return c
          })()]} repeat={[1, 100]} wrapS={THREE.RepeatWrapping} wrapT={THREE.RepeatWrapping} />
        </meshBasicMaterial>
      </mesh>
      
      {/* Brighter Tech Grid */}
      <gridHelper 
        args={[100, 100, '#3b82f6', '#1e293b']} 
        position={[0, 0.01, 0]} 
        opacity={0.3}
        transparent
      />

      {/* Walls - Glass Style */}
      {wallGeometries.map((w, i) => (
        <mesh key={`wall-${i}`} position={[w.x, 0.5, w.z]} castShadow receiveShadow material={wallMaterial}>
          <boxGeometry args={[0.9, 1.2, 0.9]} />
          <Edges threshold={15} color="#60a5fa" opacity={0.3} transparent />
        </mesh>
      ))}

      {/* POI Labels and Icons */}
      {all_pois?.map((poi, i) => {
        const px = poi.coord_x + offsetX + 0.5
        const pz = poi.coord_y + offsetZ + 0.5
        const isGuestRoom = guest_coord && poi.coord_x === guest_coord[0] && poi.coord_y === guest_coord[1]
        const isIncident = incidentData.origin_poi_id === poi.id

        return (
          <PulsingMarker 
            key={`poi-${i}`}
            position={[px, 0.05, pz]}
            color={isIncident ? '#ef4444' : (poi.type === 'room' ? (isGuestRoom ? '#3b82f6' : '#475569') : (poi.type === 'exit' || poi.type === 'stairwell' ? '#10b981' : '#f59e0b'))}
            label={poi.name}
            isIncident={isIncident}
            type={poi.type}
          />
        )
      })}

      {/* Hazards / Blocked Areas */}
      {blocked_nodes?.map((node, i) => {
        const nx = (Array.isArray(node) ? node[0] : node.x) + offsetX + 0.5
        const nz = (Array.isArray(node) ? node[1] : node.y) + offsetZ + 0.5
        return (
          <group key={`block-${i}`} position={[nx, 0.1, nz]}>
            <mesh rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[0.9, 0.9]} />
              <MeshDistortMaterial color="#ef4444" speed={5} distort={0.3} transparent opacity={0.4} />
            </mesh>
          </group>
        )
      })}

      {/* Dynamic Path */}
      {pathPoints.length > 1 && <AnimatedPath points={pathPoints} />}

      {/* Critical Markers */}
      {(() => {
        const markers = []
        
        // 1. Resolve Incident Location
        let ix = undefined, iy = undefined
        if (incidentData.origin_poi_id) {
          const origin = all_pois?.find(p => p.id === incidentData.origin_poi_id)
          if (origin) {
            ix = origin.coord_x
            iy = origin.coord_y
          }
        }

        if (ix !== undefined && iy !== undefined) {
          markers.push(
            <PulsingMarker 
              key="marker-incident"
              position={[ix + offsetX + 0.5, 0.5, iy + offsetZ + 0.5]} 
              color="#ef4444" 
              label="HAZARD"
              isIncident={true}
            />
          )
        }

        // 2. Resolve Guest/User Location
        let gx = guest_coord?.[0]
        let gy = guest_coord?.[1]
        
        if (gx !== undefined && gy !== undefined) {
          markers.push(
            <PulsingMarker 
              key="marker-guest"
              position={[gx + offsetX + 0.5, 0.5, gy + offsetZ + 0.5]} 
              color="#3b82f6" 
              label="YOU"
              isIncident={false}
            />
          )
        }

        return markers
      })()}

      {(() => {
        let ex = exit_coord?.[0]
        let ey = exit_coord?.[1]
        
        if (ex === undefined && incidentData.exit_name) {
          const exitPoi = all_pois?.find(p => p.name === incidentData.exit_name || p.id === incidentData.exit_poi_id)
          if (exitPoi) {
            ex = exitPoi.coord_x
            ey = exitPoi.coord_y
          }
        }

        if (ex !== undefined && ey !== undefined) {
          return (
            <PulsingMarker 
              position={[ex + offsetX + 0.5, 0.5, ey + offsetZ + 0.5]} 
              color="#10b981" 
              label="EXIT"
            />
          )
        }
        return null
      })()}
    </group>
  )
}

// --- 5. Main Component ---
export function Floor3DMap({ incidentData }) {
  if (!incidentData || !incidentData.static_grid || incidentData.static_grid.length === 0) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 400, color: '#475569', fontSize: 12,
        fontFamily: 'monospace', letterSpacing: 2,
        background: '#020617', borderRadius: 12, border: '1px solid #1e293b'
      }}>
        INITIALIZING 3D ENVIRONMENT...
      </div>
    )
  }

  return (
    <div style={{
      width: '100%',
      height: 450,
      background: '#020617',
      borderRadius: 16,
      border: '1px solid rgba(255, 255, 255, 0.08)',
      overflow: 'hidden',
      position: 'relative',
      boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
    }}>
      <Canvas 
        shadows 
        camera={{ position: [0, 15, 15], fov: 40 }}
        gl={{ 
          antialias: true, 
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2
        }}
        onCreated={({ gl }) => {
          gl.setClearColor('#0f172a')
          gl.shadowMap.enabled = true
          gl.shadowMap.type = THREE.PCFShadowMap
        }}
      >
        <SceneEffects />
        
        <OrbitControls 
          makeDefault
          enableDamping
          dampingFactor={0.05}
          maxPolarAngle={Math.PI / 2.2}
          minDistance={5}
          maxDistance={50}
        />
        
        <React.Suspense fallback={
          <Html center>
            <div style={{ color: '#3b82f6', fontFamily: 'monospace', fontSize: '12px', background: 'rgba(0,0,0,0.8)', padding: '8px 16px', borderRadius: '4px', border: '1px solid #1e3a5a', whiteSpace: 'nowrap' }}>
              LOADING TACTICAL ENVIRONMENT...
            </div>
          </Html>
        }>
          <GridModel incidentData={incidentData} />
        </React.Suspense>
      </Canvas>
      
      {/* Elegant Controls Info */}
      <div style={{
        position: 'absolute', bottom: 16, right: 16, pointerEvents: 'none',
        color: '#94a3b8', fontSize: 10, fontFamily: 'monospace',
        background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(8px)',
        padding: '6px 12px', borderRadius: 20,
        border: '1px solid rgba(255,255,255,0.05)',
        letterSpacing: 0.5
      }}>
        <span style={{ color: '#3b82f6' }}>Left</span> Rotate • <span style={{ color: '#3b82f6' }}>Right</span> Pan • <span style={{ color: '#3b82f6' }}>Scroll</span> Zoom
      </div>

      {/* Floor Badge */}
      <div style={{
        position: 'absolute', top: 16, right: 16,
        padding: '4px 12px', borderRadius: 12,
        background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)',
        color: '#60a5fa', fontSize: 10, fontWeight: 700, fontFamily: 'monospace'
      }}>
        3D TACTICAL VIEW
      </div>
    </div>
  )
}
