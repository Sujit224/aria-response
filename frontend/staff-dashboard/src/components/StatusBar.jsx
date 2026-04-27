import { T } from '../lib/constants'

const STATUS_CFG = {
  open:       { color: '#22c55e', label: 'LIVE' },
  connecting: { color: '#f59e0b', label: 'CONNECTING' },
  closed:     { color: '#94a3b8', label: 'RECONNECTING' },
  error:      { color: '#ef4444', label: 'ERROR' },
}

/**
 * Footer status bar — venue ID, shift time, and WS connection badge.
 * Complements TopBar (header). Shown at the bottom of the Dashboard.
 */
export function StatusBar({ wsStatus, venueId }) {
  const cfg  = STATUS_CFG[wsStatus] || STATUS_CFG.connecting
  const now  = new Date()
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const date = now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })

  return (
    <div style={{
      height: 30,
      background: T.bg,
      borderTop: `0.5px solid ${T.border}`,
      display: 'flex',
      alignItems: 'center',
      padding: '0 16px',
      gap: 16,
      flexShrink: 0,
    }}>
      <span style={{ fontSize: 9, color: T.textDim, fontFamily: T.mono, letterSpacing: 1 }}>
        {date}  {time}
      </span>

      {venueId && (
        <span style={{ fontSize: 9, color: T.textDim, fontFamily: T.mono }}>
          VENUE {venueId.slice(0, 8).toUpperCase()}
        </span>
      )}

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <div style={{ width: 5, height: 5, borderRadius: '50%', background: cfg.color }} />
        <span style={{ fontSize: 9, color: T.textDim, fontFamily: T.mono, letterSpacing: 1 }}>
          {cfg.label}
        </span>
      </div>
    </div>
  )
}
