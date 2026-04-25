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
        background:   selected ? colors.bg : T.bgCard,
        border:       `0.5px solid ${selected ? colors.border : 'rgba(59,130,246,0.12)'}`,
        borderRadius: 10,
        padding:      '12px 14px',
        cursor:       'pointer',
        transition:   'all .15s',
        marginBottom: 6,
        position:     'relative',
        fontFamily:   T.sans,
      }}
    >
      {/* Severity badge + time */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: 1,
          background: colors.badge, color: '#fff',
          padding: '2px 8px', borderRadius: 99,
        }}>
          {sevLabel}
        </span>
        <span style={{ fontSize: 10, color: T.textDim, fontFamily: T.mono }}>
          {timeAgo(incident.detected_at)}
        </span>
      </div>

      {/* Threat type */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: T.text }}>{label}</span>
      </div>

      {/* Location */}
      <div style={{ fontSize: 11, color: T.textSub, marginBottom: 4 }}>
        {incident.full_location}
      </div>

      {/* Source + pending dispatches */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontSize: 10, color: T.textDim,
          background: 'rgba(59,130,246,0.08)',
          padding: '1px 6px', borderRadius: 4,
          fontFamily: T.mono, letterSpacing: .5,
        }}>
          {incident.source === 'chat' ? 'GUEST REPORT' : 'CCTV'}
        </span>

        {pendingDispatches > 0 && (
          <span style={{
            fontSize: 10, color: '#f59e0b',
            background: 'rgba(245,158,11,0.12)',
            padding: '1px 6px', borderRadius: 99,
            fontFamily: T.mono,
          }}>
            {pendingDispatches} PENDING
          </span>
        )}
      </div>

      {/* Active pulse dot */}
      <div style={{
        position: 'absolute', top: 10, right: 10,
        width: 7, height: 7, borderRadius: '50%',
        background: colors.dot,
        boxShadow: `0 0 0 2px ${colors.dot}44`,
        animation: 'pulse-dot 2s ease-in-out infinite',
      }} />

      <style>{`
        @keyframes pulse-dot {
          0%,100% { opacity:1 } 50% { opacity:.3 }
        }
      `}</style>
    </div>
  )
}