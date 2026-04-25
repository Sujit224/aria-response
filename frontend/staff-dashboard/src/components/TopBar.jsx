import { T } from '../lib/constants'

const STATUS_CFG = {
  open:       { color: '#22c55e', label: 'LIVE' },
  connecting: { color: '#f59e0b', label: 'CONNECTING' },
  closed:     { color: '#94a3b8', label: 'RECONNECTING' },
  error:      { color: '#ef4444', label: 'ERROR' },
}

export function TopBar({ wsStatus, activeCount, criticalCount }) {
  const cfg = STATUS_CFG[wsStatus] || STATUS_CFG.connecting

  return (
    <div style={{
      height: 52,
      background: T.bg,
      borderBottom: `1px solid ${T.border}`,
      display: 'flex',
      alignItems: 'center',
      padding: '0 20px',
      gap: 20,
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontFamily: T.mono, fontSize: 16, fontWeight: 700,
        color: T.text, letterSpacing: 4,
      }}>
        <div style={{
          width: 7, height: 7, borderRadius: '50%',
          background: '#3b82f6',
          boxShadow: '0 0 8px #3b82f6',
          animation: 'pulse-dot 2s ease-in-out infinite',
        }} />
        ARIA
        <span style={{
          fontSize: 9, color: T.textDim, letterSpacing: 2,
          fontWeight: 400, marginLeft: -4,
        }}>
          STAFF OPS
        </span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Active incidents badge */}
      {activeCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontSize: 11, fontFamily: T.mono,
        }}>
          {criticalCount > 0 && (
            <span style={{
              background: 'rgba(220,38,38,0.15)',
              border: '0.5px solid rgba(220,38,38,0.4)',
              color: '#fca5a5',
              padding: '3px 10px', borderRadius: 99,
              letterSpacing: .5,
              animation: 'pulse-dot 1.2s ease-in-out infinite',
            }}>
              {criticalCount} CRITICAL
            </span>
          )}
          <span style={{
            background: 'rgba(59,130,246,0.1)',
            border: '0.5px solid rgba(59,130,246,0.25)',
            color: '#93c5fd',
            padding: '3px 10px', borderRadius: 99,
            letterSpacing: .5,
          }}>
            {activeCount} ACTIVE
          </span>
        </div>
      )}

      {/* WS status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{
          width: 7, height: 7, borderRadius: '50%',
          background: cfg.color,
        }} />
        <span style={{ fontSize: 10, color: T.textDim, fontFamily: T.mono, letterSpacing: 1 }}>
          {cfg.label}
        </span>
      </div>

      <style>{`
        @keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.4} }
      `}</style>
    </div>
  )
}