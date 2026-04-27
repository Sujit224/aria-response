const STATUS_CFG = {
  open:       { color: '#22c55e', label: 'Connected', dot: true },
  connecting: { color: '#f59e0b', label: 'Connecting…', dot: true },
  closed:     { color: '#f59e0b', label: 'Reconnecting…', dot: true },
  error:      { color: '#ef4444', label: 'Connection error', dot: true },
}

export function StatusBar({ wsStatus, roomName, floorInfo }) {
  const cfg = STATUS_CFG[wsStatus] || STATUS_CFG.connecting

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 16px',
      background: 'rgba(5,10,15,0.95)',
      borderBottom: '0.5px solid rgba(59,130,246,0.15)',
      flexShrink: 0,
      gap: 10,
    }}>
      {/* Room info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: '#3b82f6',
          boxShadow: '0 0 6px #3b82f6',
        }} />
        <span style={{
          fontSize: 13, fontWeight: 600,
          color: '#e2f0ff',
          fontFamily: "'Inter', system-ui, sans-serif",
        }}>
          {roomName || 'Unknown Room'}
        </span>
        {floorInfo && (
          <span style={{ fontSize: 11, color: '#475569', fontFamily: 'monospace' }}>
            {floorInfo}
          </span>
        )}
      </div>

      {/* WS status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: cfg.color,
          animation: wsStatus === 'open' ? 'none' : 'blink 1s ease-in-out infinite',
        }} />
        <span style={{ fontSize: 10, color: '#64748b', fontFamily: 'monospace', letterSpacing: 0.5 }}>
          {cfg.label}
        </span>
      </div>

      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }`}</style>
    </div>
  )
}
