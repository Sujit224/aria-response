import { SEV_COLOR, SEV_LABEL, THREAT_ICON, THREAT_LABEL, T } from '../lib/constants'

function timeAgo(iso) {
  const secs = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (secs < 60)   return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  return `${Math.floor(secs / 3600)}h ago`
}

export function IncidentCard({ incident, selected, onSelect }) {
  const sevLabel  = SEV_LABEL[incident.severity] || 'MEDIUM'
  const colors    = SEV_COLOR[sevLabel] || SEV_COLOR.MEDIUM
  const icon      = THREAT_ICON[incident.type]  || '⚠'
  const label     = THREAT_LABEL[incident.type] || incident.type

  const pendingDispatches = (incident.dispatches || []).filter(
    d => d.ack_status === 'PENDING'
  ).length

  return (
    <div
      onClick={() => onSelect(incident)}
      style={{
        background:   selected ? colors.bg : 'rgba(30, 41, 59, 0.4)',
        border:       `1px solid ${selected ? colors.border : 'rgba(255,255,255,0.08)'}`,
        borderRadius: 14,
        padding:      '18px',
        cursor:       'pointer',
        transition:   'all .3s cubic-bezier(0.4, 0, 0.2, 1)',
        marginBottom: 12,
        position:     'relative',
        fontFamily:   T.sans,
        boxShadow:    selected ? `0 10px 30px ${colors.border}33` : '0 4px 12px rgba(0,0,0,0.1)',
        backdropFilter: 'blur(8px)',
        transform:    selected ? 'scale(1.02)' : 'scale(1)',
        zIndex:       selected ? 10 : 1,
      }}
      onMouseOver={e => { 
        if (!selected) {
          e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)'
          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)'
          e.currentTarget.style.transform = 'translateY(-2px)'
        }
      }}
      onMouseOut={e => { 
        if (!selected) {
          e.currentTarget.style.background = 'rgba(30, 41, 59, 0.4)'
          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)'
          e.currentTarget.style.transform = 'scale(1)'
        }
      }}
    >
      {/* Severity badge + time */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{
          fontSize: 9, fontWeight: 800, letterSpacing: 1.5,
          background: colors.badge, color: '#fff',
          padding: '3px 10px', borderRadius: 99,
          textTransform: 'uppercase',
          boxShadow: `0 0 10px ${colors.badge}44`
        }}>
          {sevLabel}
        </span>
        <span style={{ fontSize: 10, color: T.textDim, fontFamily: T.mono, opacity: 0.7 }}>
          {timeAgo(incident.detected_at)}
        </span>
      </div>

      {/* Threat type */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <span style={{ 
          fontSize: 18, 
          filter: selected ? 'drop-shadow(0 0 5px rgba(255,255,255,0.3))' : 'none' 
        }}>{icon}</span>
        <span style={{ 
          fontSize: 14, 
          fontWeight: 700, 
          color: selected ? '#fff' : T.text,
          letterSpacing: 0.3
        }}>{label}</span>
      </div>

      {/* Location */}
      <div style={{ 
        fontSize: 11, 
        color: selected ? 'rgba(255,255,255,0.8)' : T.textSub, 
        marginBottom: 10,
        lineHeight: 1.4
      }}>
        {incident.full_location}
      </div>

      {/* Source + pending dispatches */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{
            fontSize: 9, color: T.textDim,
            background: 'rgba(255,255,255,0.05)',
            padding: '2px 8px', borderRadius: 6,
            fontFamily: T.mono, letterSpacing: 1,
            fontWeight: 600,
            border: '1px solid rgba(255,255,255,0.03)'
          }}>
            {incident.source === 'chat' ? 'GUEST' : 'CCTV'}
          </span>
        </div>

        {pendingDispatches > 0 && (
          <div style={{
            fontSize: 10, color: '#fbbf24',
            background: 'rgba(251,191,36,0.1)',
            padding: '3px 10px', borderRadius: 99,
            fontFamily: T.mono,
            fontWeight: 700,
            border: '1px solid rgba(251,191,36,0.2)',
            display: 'flex', alignItems: 'center', gap: 4
          }}>
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#fbbf24' }} />
            {pendingDispatches} PENDING
          </div>
        )}
      </div>

      {/* Active pulse dot */}
      <div style={{
        position: 'absolute', top: 18, right: 18,
        width: 8, height: 8, borderRadius: '50%',
        background: colors.dot,
        boxShadow: `0 0 10px ${colors.dot}`,
        animation: 'pulse-dot 1.5s ease-in-out infinite',
      }} />

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}