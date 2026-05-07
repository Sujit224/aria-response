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

const FLOOR_H    = 32   // px height per floor slab
const FLOOR_W    = 130  // px width of each block
const BLOCK_GAP  = 48   // px gap between blocks
const DEPTH      = 20   // px 3D depth

function FloorSlab({ floor, blockCode, hasIncident, isSelected, onClick, isTop }) {
  const [hovered, setHovered] = useState(false)

  const baseColor  = hasIncident
    ? (isSelected ? 'rgba(239,68,68,0.7)' : 'rgba(239,68,68,0.25)')
    : (isSelected  ? 'rgba(59,130,246,0.65)' : 'rgba(59,130,246,0.08)')

  const borderColor = hasIncident
    ? (isSelected ? '#ef4444' : 'rgba(239,68,68,0.5)')
    : (isSelected  ? '#60a5fa' : hovered ? 'rgba(59,130,246,0.4)' : 'rgba(59,130,246,0.15)')

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
        borderRadius: isTop ? '8px 8px 0 0' : 0,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 12px',
        transition: 'all .2s cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'relative',
        marginBottom: 1,
        boxShadow: isSelected ? `0 0 15px ${hasIncident ? '#ef4444' : '#3b82f6'}44` : 'none',
        zIndex: isSelected ? 5 : 1,
      }}
    >
      <span style={{
        fontSize: 10, fontFamily: T.mono, letterSpacing: 1.5,
        color: isSelected ? '#fff' : T.textSub,
        fontWeight: isSelected ? 700 : 400,
        textShadow: isSelected ? '0 0 10px rgba(255,255,255,0.5)' : 'none',
      }}>
        F{floor.level}
      </span>
      {hasIncident && (
        <span style={{
          width: 8, height: 8, borderRadius: '50%',
          background: '#ef4444',
          boxShadow: '0 0 8px #ef4444',
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
        fontSize: 10, fontFamily: T.mono, letterSpacing: 2.5,
        color: '#60a5fa', marginBottom: 10, fontWeight: 700,
        textTransform: 'uppercase',
        opacity: 0.8,
      }}>
        BLOCK {block.block_code}
      </div>

      {/* 3D container */}
      <div style={{
        position: 'relative',
        transform: 'perspective(500px) rotateX(15deg)',
        transformOrigin: 'center bottom',
        transition: 'transform 0.4s ease',
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
          background: 'linear-gradient(to right, rgba(59,130,246,0.15), rgba(59,130,246,0.02))',
          borderLeft: '1px solid rgba(59,130,246,0.15)',
          transform: 'skewY(-45deg)',
          transformOrigin: 'top left',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', bottom: -DEPTH/2, left: 0,
          width: FLOOR_W + DEPTH, height: DEPTH/2,
          background: 'rgba(59,130,246,0.04)',
          borderTop: '1px solid rgba(59,130,246,0.1)',
          pointerEvents: 'none',
        }} />
      </div>

      <div style={{ 
        fontSize: 9, color: T.textDim, marginTop: 12, 
        fontFamily: T.mono, letterSpacing: 1,
        opacity: 0.6
      }}>
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
        height: 120, color: T.textDim, fontSize: 11,
        fontFamily: T.mono, letterSpacing: 1,
        border: `1px dashed ${T.border}`, borderRadius: 12,
        margin: '16px 20px'
      }}>
        INITIALIZING BUILDING DATA...
      </div>
    )
  }

  return (
    <div style={{ 
      padding: '20px', 
      background: 'rgba(15, 23, 42, 0.4)',
      borderTop: `1px solid ${T.border}`,
      boxShadow: 'inset 0 10px 30px rgba(0,0,0,0.2)'
    }}>
      <div style={{
        fontSize: 10, letterSpacing: 3, color: '#94a3b8',
        fontFamily: T.mono, fontWeight: 700, marginBottom: 20,
        textAlign: 'center', opacity: 0.8
      }}>
        BUILDING OVERVIEW
      </div>
      <div style={{
        display: 'flex', gap: BLOCK_GAP,
        overflowX: 'auto', paddingBottom: 24,
        alignItems: 'flex-end',
        justifyContent: blocks.length < 3 ? 'center' : 'flex-start',
        scrollbarWidth: 'none',
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
      <style>{`
        @keyframes pulse-dot { 0%,100%{opacity:1; transform:scale(1)} 50%{opacity:.4; transform:scale(1.2)} }
        ::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  )
}

