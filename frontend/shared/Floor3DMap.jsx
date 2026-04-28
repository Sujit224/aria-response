import React, { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Line, Edges } from '@react-three/drei'
import * as THREE from 'three'

function GridModel({ incidentData }) {
  const {
    static_grid, guest_coord, exit_coord, path_update,
    blocked_nodes, all_pois
  } = incidentData

  const grid_height = incidentData.grid_height || static_grid.length
  const grid_width = incidentData.grid_width || (static_grid[0] ? static_grid[0].length : 0)

  // Center the map
  const offsetX = -grid_width / 2
  const offsetZ = -grid_height / 2

  // 1. Generate walls
  const walls = []
  for (let y = 0; y < grid_height; y++) {
    for (let x = 0; x < grid_width; x++) {
      if (static_grid[y][x] === 1) {
        walls.push({ x: x + offsetX + 0.5, z: y + offsetZ + 0.5 })
      }
    }
  }

  // 2. Generate Evacuation Path Points
  const pathPoints = useMemo(() => {
    if (!path_update) return []
    return path_update.map(p => new THREE.Vector3(
      p[0] + offsetX + 0.5,
      0.1,
      p[1] + offsetZ + 0.5
    ))
  }, [path_update, offsetX, offsetZ])

  // Material configs
  const wallMaterial = useMemo(() => new THREE.MeshStandardMaterial({ 
    color: '#1e293b', 
    roughness: 0.7, 
    metalness: 0.2 
  }), [])

  return (
    <group>
      {/* Floor Plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[grid_width * 1.5, grid_height * 1.5]} />
        <meshStandardMaterial color="#020617" roughness={0.8} />
      </mesh>
      
      {/* Subtle grid on floor */}
      <gridHelper args={[Math.max(grid_width, grid_height) * 1.5, Math.max(grid_width, grid_height) * 1.5, '#1e293b', '#0f172a']} position={[0, 0.01, 0]} />

      {/* Walls */}
      {walls.map((w, i) => (
        <mesh key={`wall-${i}`} position={[w.x, 0.5, w.z]} castShadow receiveShadow material={wallMaterial}>
          <boxGeometry args={[1, 1, 1]} />
          <Edges scale={1} threshold={15} color="#334155" />
        </mesh>
      ))}

      {/* POIs */}
      {all_pois?.map((poi, i) => {
        const px = poi.coord_x + offsetX + 0.5
        const pz = poi.coord_y + offsetZ + 0.5
        const isGuestRoom = guest_coord && poi.coord_x === guest_coord[0] && poi.coord_y === guest_coord[1]

        if (poi.type === 'room') {
          return (
            <group key={`poi-${i}`} position={[px, 0.05, pz]}>
              <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
                <planeGeometry args={[0.9, 0.9]} />
                <meshStandardMaterial color={isGuestRoom ? '#2563eb' : '#1e293b'} opacity={0.8} transparent />
              </mesh>
              <Text
                position={[0, 0.05, 0]}
                rotation={[-Math.PI / 2, 0, 0]}
                fontSize={0.25}
                color={isGuestRoom ? '#93c5fd' : '#94a3b8'}
                anchorX="center"
                anchorY="middle"
                font="https://fonts.gstatic.com/s/inter/v12/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2"
              >
                {poi.name}
              </Text>
            </group>
          )
        } else if (poi.type === 'medical') {
          return (
            <group key={`poi-${i}`} position={[px, 0.3, pz]}>
              <mesh castShadow receiveShadow>
                <boxGeometry args={[0.6, 0.6, 0.6]} />
                <meshStandardMaterial color="#b91c1c" />
              </mesh>
              <Text position={[0, 0.5, 0]} fontSize={0.3} color="#fca5a5" anchorX="center" anchorY="bottom">
                AID
              </Text>
            </group>
          )
        } else if (poi.type === 'exit' || poi.type === 'stairwell') {
          return (
            <group key={`poi-${i}`} position={[px, 0.4, pz]}>
              <mesh castShadow receiveShadow>
                <boxGeometry args={[0.8, 0.8, 0.2]} />
                <meshStandardMaterial color="#047857" />
              </mesh>
              <Text position={[0, 0.6, 0]} fontSize={0.3} color="#6ee7b7" anchorX="center" anchorY="bottom">
                {poi.type.toUpperCase()}
              </Text>
            </group>
          )
        }
        return null
      })}

      {/* Blocked Nodes */}
      {blocked_nodes?.map((node, i) => {
        const nx = (Array.isArray(node) ? node[0] : node.x) + offsetX + 0.5
        const nz = (Array.isArray(node) ? node[1] : node.y) + offsetZ + 0.5
        return (
          <group key={`block-${i}`} position={[nx, 0.1, nz]}>
            <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
              <planeGeometry args={[1, 1]} />
              <meshBasicMaterial color="#ef4444" opacity={0.3} transparent />
            </mesh>
            <Text position={[0, 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.6} color="#ef4444" anchorX="center" anchorY="middle">
              X
            </Text>
          </group>
        )
      })}

      {/* Evacuation Path */}
      {pathPoints.length > 1 && (
        <AnimatedPath points={pathPoints} />
      )}

      {/* Guest Location */}
      {guest_coord && (
        <PulsingMarker 
          position={[guest_coord[0] + offsetX + 0.5, 0.2, guest_coord[1] + offsetZ + 0.5]} 
          color="#3b82f6" 
          label="YOU"
        />
      )}

      {/* Exit / Target Location */}
      {exit_coord && (
        <PulsingMarker 
          position={[exit_coord[0] + offsetX + 0.5, 0.2, exit_coord[1] + offsetZ + 0.5]} 
          color="#10b981" 
          label="TARGET"
        />
      )}
    </group>
  )
}

function AnimatedPath({ points }) {
  const lineRef = useRef()
  const dashOffset = useRef(0)

  useFrame((state, delta) => {
    if (lineRef.current) {
      dashOffset.current -= delta * 2
      lineRef.current.material.dashOffset = dashOffset.current
    }
  })

  return (
    <Line
      ref={lineRef}
      points={points}
      color="#22c55e"
      lineWidth={4}
      dashed
      dashSize={0.5}
      dashScale={1}
      gapSize={0.3}
    />
  )
}

function PulsingMarker({ position, color, label }) {
  const meshRef = useRef()
  const ringRef = useRef()

  useFrame((state) => {
    const time = state.clock.getElapsedTime()
    if (meshRef.current) {
      meshRef.current.position.y = position[1] + Math.sin(time * 3) * 0.1
    }
    if (ringRef.current) {
      const scale = 1 + (time % 1) * 2
      ringRef.current.scale.set(scale, scale, scale)
      ringRef.current.material.opacity = Math.max(0, 1 - (time % 1))
    }
  })

  return (
    <group position={position}>
      {/* Center sphere */}
      <mesh ref={meshRef} castShadow>
        <sphereGeometry args={[0.25, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
      </mesh>
      
      {/* Pulsing ring */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.19, 0]}>
        <ringGeometry args={[0.25, 0.35, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
      
      {/* Floating Label */}
      <Text position={[0, 0.7, 0]} fontSize={0.25} color={color} anchorX="center" anchorY="bottom" outlineWidth={0.02} outlineColor="#000">
        {label}
      </Text>
    </group>
  )
}

export function Floor3DMap({ incidentData }) {
  if (!incidentData || !incidentData.static_grid || incidentData.static_grid.length === 0) {
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
    <div style={{
      width: '100%',
      height: 400,
      background: '#020617',
      borderRadius: 12,
      border: '1px solid #1e293b',
      overflow: 'hidden',
      position: 'relative'
    }}>
      <Canvas shadows camera={{ position: [0, 10, 10], fov: 45 }}>
        {/* Environment Lighting */}
        <ambientLight intensity={0.3} />
        <directionalLight 
          castShadow 
          position={[10, 15, 5]} 
          intensity={1.2} 
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <pointLight position={[-10, 10, -10]} intensity={0.5} color="#3b82f6" />
        
        <OrbitControls 
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          maxPolarAngle={Math.PI / 2.1} // Prevent looking from below
        />
        
        {incidentData?.static_grid && (
          <GridModel incidentData={incidentData} />
        )}
      </Canvas>
      
      {/* Overlay controls hint */}
      <div style={{
        position: 'absolute', bottom: 12, right: 12, pointerEvents: 'none',
        color: '#64748b', fontSize: 10, fontFamily: 'monospace',
        background: 'rgba(2, 6, 23, 0.7)', padding: '4px 8px', borderRadius: 4,
        border: '1px solid #1e293b'
      }}>
        Left Click: Rotate • Right Click: Pan • Scroll: Zoom
      </div>
    </div>
  )
}
