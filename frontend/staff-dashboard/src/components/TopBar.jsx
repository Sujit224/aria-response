import { T } from '../lib/constants'

const STATUS_CFG = {
  open:       { color: '#22c55e', label: 'SYSTEM LIVE' },
  connecting: { color: '#f59e0b', label: 'CONNECTING' },
  closed:     { color: '#94a3b8', label: 'RECONNECTING' },
  error:      { color: '#ef4444', label: 'ERROR' },
}

export function TopBar({ wsStatus, activeCount, criticalCount, onGoQR }) {
  const cfg = STATUS_CFG[wsStatus] || STATUS_CFG.connecting

  return (
    <div style={{
      height: 60,
      background: 'rgba(5, 10, 15, 0.85)',
      backdropFilter: 'blur(12px)',
      borderBottom: `1px solid rgba(255, 255, 255, 0.05)`,
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      gap: 20,
      flexShrink: 0,
      zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: T.mono, fontSize: 18, fontWeight: 700,
        color: '#f8fafc', letterSpacing: 3,
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: '#3b82f6',
          boxShadow: '0 0 12px #3b82f6',
          animation: 'pulse-dot 2s ease-in-out infinite',
        }} />
        ARIA
        <div style={{
          fontSize: 10, color: '#94a3b8', letterSpacing: 2,
          fontWeight: 500, paddingLeft: 6, borderLeft: '1px solid rgba(255,255,255,0.1)'
        }}>
          STAFF OPS
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* QR Codes Link */}
      {onGoQR && (
        <button
          onClick={onGoQR}
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#cbd5e1', borderRadius: 8,
            padding: '8px 16px', fontSize: 11,
            fontFamily: T.mono, fontWeight: 600,
            cursor: 'pointer', letterSpacing: 1,
            transition: 'all 0.2s',
          }}
          onMouseOver={e => e.target.style.background = 'rgba(255, 255, 255, 0.08)'}
          onMouseOut={e => e.target.style.background = 'rgba(255, 255, 255, 0.03)'}
        >
          ROOM QR CODES
        </button>
      )}

      {/* Active incidents badge */}
      {activeCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 11, fontFamily: T.mono, fontWeight: 600
        }}>
          {criticalCount > 0 && (
            <span style={{
              background: 'rgba(220,38,38,0.15)',
              border: '1px solid rgba(220,38,38,0.3)',
              color: '#fca5a5',
              padding: '6px 12px', borderRadius: 6,
              letterSpacing: 1,
              animation: 'pulse-dot 1.2s ease-in-out infinite',
            }}>
              {criticalCount} CRITICAL
            </span>
          )}
          <span style={{
            background: 'rgba(59,130,246,0.1)',
            border: '1px solid rgba(59,130,246,0.2)',
            color: '#93c5fd',
            padding: '6px 12px', borderRadius: 6,
            letterSpacing: 1,
          }}>
            {activeCount} ACTIVE
          </span>
        </div>
      )}

      {/* WS status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: cfg.color,
          boxShadow: `0 0 8px ${cfg.color}`
        }} />
        <span style={{ fontSize: 11, color: '#94a3b8', fontFamily: T.mono, letterSpacing: 1, fontWeight: 600 }}>
          {cfg.label}
        </span>
      </div>

      <style>{`
        @keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.4} }
      `}</style>
    </div>
  )
}