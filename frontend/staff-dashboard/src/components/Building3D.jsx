import React, { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Edges, Float, MeshDistortMaterial } from '@react-three/drei'
import * as THREE from 'three'

const T = {
  bg: '#0f172a',
  accent: '#3b82f6',
  danger: '#ef4444',
  text: '#f8fafc',
}

function FloorSlab({ floor, index, totalFloors, incidentsOnFloor }) {
  const isDanger = incidentsOnFloor.length > 0
  
  // Center the grid coordinates
  const offsetX = -floor.grid_width / 2
  const offsetZ = -floor.grid_height / 2
  const scale = 2.0 

  return (
    <group position={[0, index * 12, 0]}>
      {/* Tactical Floor Plate */}
      <mesh receiveShadow castShadow>
        <boxGeometry args={[floor.grid_width * scale + 2, 0.2, floor.grid_height * scale + 2]} />
        <meshStandardMaterial 
          color={isDanger ? '#2a0a0a' : '#0f172a'} 
          transparent 
          opacity={0.9}
          metalness={0.8}
          roughness={0.2}
        />
        <Edges color={isDanger ? '#ef4444' : '#3b82f6'} opacity={isDanger ? 0.6 : 0.3} transparent />
      </mesh>

      {/* Grid Overlay */}
      <gridHelper 
        args={[floor.grid_width * scale, floor.grid_width, '#1e293b', '#0f172a']} 
        position={[0, 0.15, 0]} 
        opacity={0.2} 
        transparent 
      />

      {/* Proper Room Structure (Flat, occupying grid cells) */}
      <group>
        {floor.pois?.map((poi) => {
          const isExit = poi.type === 'exit' || poi.type === 'stairwell'
          const poiIncidents = incidentsOnFloor.filter(inc => inc.origin_poi_id === poi.id)
          const isPoiDanger = poiIncidents.length > 0

          const x = (poi.coord_x + offsetX) * scale + (scale / 2)
          const z = (poi.coord_y + offsetZ) * scale + (scale / 2)
          
          // Rooms are flat, filling the grid cell
          const roomWidth = scale * 0.95
          const roomHeight = 1.2
          const roomDepth = scale * 0.95

          return (
            <group key={poi.id} position={[x, roomHeight / 2 + 0.1, z]}>
              {/* Room Volume */}
              <mesh>
                <boxGeometry args={[roomWidth, roomHeight, roomDepth]} />
                <meshStandardMaterial 
                  color={isExit ? '#10b981' : (isPoiDanger ? '#ef4444' : '#3b82f6')} 
                  transparent 
                  opacity={isPoiDanger ? 0.6 : 0.2} 
                  emissive={isExit ? '#10b981' : (isPoiDanger ? '#ef4444' : '#3b82f6')}
                  emissiveIntensity={isPoiDanger ? 0.8 : 0.2}
                />
              </mesh>
              {/* Room Skeleton/Walls */}
              <mesh>
                <boxGeometry args={[roomWidth + 0.05, roomHeight + 0.05, roomDepth + 0.05]} />
                <meshBasicMaterial 
                  color={isExit ? '#34d399' : (isPoiDanger ? '#f87171' : '#60a5fa')} 
                  wireframe 
                  opacity={isPoiDanger ? 1 : 0.4} 
                  transparent 
                />
              </mesh>

              {/* Individual Incident Marker Beams per POI */}
              {isPoiDanger && (
                <group position={[0, 0, 0]}>
                  <pointLight color={T.danger} intensity={15} distance={30} />
                  <mesh position={[0, 50, 0]}>
                    <cylinderGeometry args={[0.3, 0.3, 100, 16, 1, true]} />
                    <meshBasicMaterial 
                      color={T.danger} 
                      transparent 
                      opacity={0.4} 
                      blending={THREE.AdditiveBlending} 
                      side={THREE.DoubleSide}
                    />
                  </mesh>
                </group>
              )}
            </group>
          )
        })}
      </group>

      {/* Minimal Level Label */}
      <Text
        position={[-(floor.grid_width * scale / 2) - 6, 0, 0]}
        fontSize={2}
        color={isDanger ? T.danger : '#64748b'}
        anchorX="right"
        fontWeight={800}
      >
        L{floor.level}
      </Text>
    </group>
  )
}

function BuildingModel({ blocks, incidents }) {
  const incidentsByFloor = useMemo(() => {
    const map = {}
    incidents.forEach(inc => {
      if (!map[inc.floor_id]) map[inc.floor_id] = []
      map[inc.floor_id].push(inc)
    })
    return map
  }, [incidents])


  // Center horizontally based on all blocks
  const blockGap = 100
  const totalW = (blocks.length - 1) * blockGap
  
  const maxFloors = Math.max(...blocks.map(b => b.floors?.length || 0))
  const yOffset = -(maxFloors * 7.5) // Adjust centering based on floor spacing

  return (
    <group position={[0, yOffset, 0]}>
      {blocks.map((block, bIdx) => {
        const posX = (bIdx * blockGap) - (totalW / 2)
        const maxBlockW = Math.max(...block.floors.map(f => f.grid_width))
        const maxBlockH = Math.max(...block.floors.map(f => f.grid_height))
        const scale = 2.0
        
        const floorCount = block.floors?.length || 0
        const buildingHeight = (floorCount > 0 ? (floorCount - 1) * 12 : 0) + 8
        const centerY = (floorCount > 0 ? (floorCount - 1) * 12 : 0) / 2

        return (
          <group key={block.block_id} position={[posX, 0, 0]}>
            {/* Tactical Block Designation */}
            <Text
              position={[0, buildingHeight + 10, 0]}
              fontSize={5}
              color="#60a5fa"
              opacity={0.8}
              transparent
              fontWeight={900}
              letterSpacing={0.1}
            >
              {`BLOCK-${block.block_code}`.toUpperCase()}
            </Text>

            {/* Central Elevator/Structural Core */}
            {floorCount > 0 && (
              <mesh position={[0, centerY, 0]}>
                <boxGeometry args={[4, buildingHeight, 4]} />
                <meshStandardMaterial color="#0f172a" metalness={0.6} roughness={0.5} />
                <Edges color="#1e293b" opacity={0.5} />
              </mesh>
            )}

            {/* Glass Architectural Facade */}
            {floorCount > 0 && (
              <mesh position={[0, centerY, 0]}>
                <boxGeometry args={[maxBlockW * scale + 6, buildingHeight, maxBlockH * scale + 6]} />
                <meshStandardMaterial 
                  color="#3b82f6" 
                  opacity={0.08} 
                  transparent 
                  roughness={0.2}
                  metalness={0.5}
                  side={THREE.DoubleSide}
                  depthWrite={false}
                />
                <Edges color="#3b82f6" opacity={0.15} transparent />
              </mesh>
            )}

            {/* Floors */}
            {block.floors?.map((floor, fIdx) => (
              <FloorSlab 
                key={floor.floor_id} 
                floor={floor} 
                index={fIdx} 
                totalFloors={block.floors.length}
                incidentsOnFloor={incidentsByFloor[floor.floor_id] || []}
              />
            ))}

            {/* Solid Foundation */}
            <mesh position={[0, -2, 0]}>
              <boxGeometry args={[maxBlockW * scale + 10, 4, maxBlockH * scale + 10]} />
              <meshStandardMaterial color="#020617" metalness={1} roughness={0.1} />
              <Edges color="#1e293b" />
            </mesh>
          </group>
        )
      })}

      <gridHelper args={[800, 40, '#1e293b', '#020617']} position={[0, -4.1, 0]} />
    </group>
  )
}

export default function Building3D({ blocks, incidents }) {
  if (!blocks || blocks.length === 0) return null

  return (
    <div style={{ width: '100%', height: '100%', background: '#020617', borderRadius: 12, overflow: 'hidden' }}>
      <Canvas shadows camera={{ position: [-150, 120, 180], fov: 35 }}>
        <fog attach="fog" args={['#020617', 150, 600]} />
        
        <ambientLight intensity={0.5} />
        <pointLight position={[200, 200, 200]} intensity={1.5} />
        <pointLight position={[-200, 100, -100]} intensity={0.8} color="#3b82f6" />
        <spotLight position={[0, 300, 0]} intensity={1} angle={0.3} penumbra={1} castShadow />

        <BuildingModel blocks={blocks} incidents={incidents} />

        <OrbitControls 
          enableDamping 
          dampingFactor={0.05} 
          maxPolarAngle={Math.PI / 2.1}
          minDistance={80}
          maxDistance={600}
        />
      </Canvas>

      {/* UI Overlay */}
      <div style={{
        position: 'absolute', top: 20, left: 20,
        padding: '12px 20px', borderRadius: 8,
        background: 'rgba(15, 23, 42, 0.8)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        pointerEvents: 'none'
      }}>
        <div style={{ fontSize: 10, color: T.accent, fontWeight: 800, letterSpacing: 1, marginBottom: 4 }}>GLOBAL TACTICAL VIEW</div>
        <div style={{ fontSize: 14, color: '#fff', fontWeight: 600 }}>BUILDING OVERVIEW</div>
      </div>
    </div>
  )
}
