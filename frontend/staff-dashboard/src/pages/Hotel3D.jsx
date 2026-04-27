import { useEffect, useRef, useState } from 'react'
import { T } from '../lib/constants'

/**
 * Hotel3D.jsx
 * ───────────
 * Interactive 3D-style hotel block navigator using pure CSS perspective transforms.
 * No Three.js dependency needed — this uses layered CSS for a convincing 3D block view.
 *
 * Props:
 *   blocks    — [{block_code, name, floors:[{floor_id, level}]}]
 *   incidents — active incidents keyed by floor_id
 *   onSelect  — (floor_id) => void — called when a floor is clicked
 *   selected  — currently selected floor_id
 */

const FLOOR_H    = 28   // px height per floor slab
const FLOOR_W    = 120  // px width of each block
const BLOCK_GAP  = 40   // px gap between blocks
const DEPTH      = 18   // px 3D depth

function FloorSlab({ floor, blockCode, hasIncident, isSelected, onClick, isTop }) {
  const [hovered, setHovered] = useState(false)

  const baseColor  = hasIncident
    ? (isSelected ? 'rgba(220,38,38,0.6)' : 'rgba(220,38,38,0.25)')
    : (isSelected  ? 'rgba(59,130,246,0.55)' : 'rgba(59,130,246,0.08)')

  const borderColor = hasIncident
    ? (isSelected ? '#dc2626' : 'rgba(220,38,38,0.5)')
    : (isSelected  ? '#3b82f6' : hovered ? 'rgba(59,130,246,0.4)' : 'rgba(59,130,246,0.15)')

  return (
    <div
      onClick={() => onClick(floor.floor_id)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={`${blockCode}-F${floor.level}`}
      style={{
        width: FLOOR_W,
        height: FLOOR_H,
        background: hovered && !isSelected ? 'rgba(59,130,246,0.15)' : baseColor,
        border: `1px solid ${borderColor}`,
        borderRadius: isTop ? '6px 6px 0 0' : 0,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 10px',
        transition: 'all .15s',
        position: 'relative',
        marginBottom: 1,
      }}
    >
      <span style={{
        fontSize: 9, fontFamily: T.mono, letterSpacing: 1,
        color: isSelected ? '#fff' : T.textSub,
        fontWeight: isSelected ? 600 : 400,
      }}>
        F{floor.level}
      </span>
      {hasIncident && (
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: '#dc2626',
          boxShadow: '0 0 6px #dc2626',
          animation: 'pulse-dot 1.2s ease-in-out infinite',
          flexShrink: 0,
        }} />
      )}
    </div>
  )
}

function Block3D({ block, incidents, selected, onSelect }) {
  const sortedFloors = [...(block.floors || [])].sort((a, b) => b.level - a.level)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0 }}>
      {/* Block label */}
      <div style={{
        fontSize: 10, fontFamily: T.mono, letterSpacing: 2,
        color: '#3b82f6', marginBottom: 6, fontWeight: 600,
      }}>
        BLOCK {block.block_code}
      </div>

      {/* 3D container */}
      <div style={{
        position: 'relative',
        transform: 'perspective(400px) rotateX(12deg)',
        transformOrigin: 'center bottom',
      }}>
        {sortedFloors.map((floor, i) => (
          <FloorSlab
            key       = {floor.floor_id}
            floor     = {floor}
            blockCode = {block.block_code}
            hasIncident = {!!incidents?.[floor.floor_id]}
            isSelected  = {selected === floor.floor_id}
            onClick     = {onSelect}
            isTop       = {i === 0}
          />
        ))}

        {/* 3D depth sides */}
        <div style={{
          position: 'absolute', top: 0, right: -DEPTH,
          width: DEPTH, height: '100%',
          background: 'linear-gradient(to right, rgba(59,130,246,0.15), rgba(59,130,246,0.04))',
          borderLeft: '1px solid rgba(59,130,246,0.12)',
          transform: 'skewY(-45deg)',
          transformOrigin: 'top left',
        }} />
        <div style={{
          position: 'absolute', bottom: -DEPTH/2, left: 0,
          width: FLOOR_W + DEPTH, height: DEPTH/2,
          background: 'rgba(59,130,246,0.06)',
          borderTop: '1px solid rgba(59,130,246,0.1)',
        }} />
      </div>

      <div style={{ fontSize: 9, color: T.textDim, marginTop: 8, fontFamily: T.mono }}>
        {block.name || ''}
      </div>
    </div>
  )
}


export function Hotel3D({ blocks = [], incidents = [], selected, onSelect }) {
  // Build a lookup: floor_id → incident
  const incidentByFloor = {}
  incidents.forEach(inc => {
    if (inc.floor_id) incidentByFloor[inc.floor_id] = inc
  })

  if (!blocks.length) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 200, color: T.textDim, fontSize: 12,
        fontFamily: T.mono, letterSpacing: 1,
      }}>
        NO VENUE DATA
      </div>
    )
  }

  return (
    <div style={{ padding: '16px 20px' }}>
      <div style={{
        fontSize: 9, letterSpacing: 2, color: '#3b82f6',
        fontFamily: T.mono, fontWeight: 600, marginBottom: 16,
      }}>
        HOTEL OVERVIEW — SELECT FLOOR
      </div>
      <div style={{
        display: 'flex', gap: BLOCK_GAP,
        overflowX: 'auto', paddingBottom: 20,
        alignItems: 'flex-end',
      }}>
        {blocks.map(block => (
          <Block3D
            key       = {block.block_code}
            block     = {block}
            incidents = {incidentByFloor}
            selected  = {selected}
            onSelect  = {onSelect}
          />
        ))}
      </div>
      <style>{`@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.3} }`}</style>
    </div>
  )
}
