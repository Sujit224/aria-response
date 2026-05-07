const S = {
  bubble: {
    display: 'flex',
    marginBottom: 16,
  },
  inner: (fromAria) => ({
    maxWidth: '85%',
    padding: '12px 16px',
    borderRadius: fromAria ? '4px 20px 20px 20px' : '20px 4px 20px 20px',
    background: fromAria
      ? 'rgba(30, 41, 59, 0.8)' // slate-800
      : 'linear-gradient(135deg, #2563eb, #3b82f6)', // blue
    border: fromAria
      ? '1px solid rgba(255,255,255,0.05)'
      : 'none',
    boxShadow: fromAria
      ? '0 4px 12px rgba(0,0,0,0.2)'
      : '0 4px 12px rgba(59,130,246,0.3)',
    marginLeft:  fromAria ? 0 : 'auto',
    marginRight: fromAria ? 'auto' : 0,
    backdropFilter: 'blur(8px)',
  }),
  text: (fromAria) => ({
    fontSize: 14,
    lineHeight: 1.5,
    color: fromAria ? '#e2e8f0' : '#ffffff',
    fontFamily: "'Inter', system-ui, sans-serif",
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  }),
  time: (fromAria) => ({
    fontSize: 10,
    color: fromAria ? '#64748b' : 'rgba(255,255,255,0.7)',
    marginTop: 6,
    fontFamily: 'monospace',
    textAlign: fromAria ? 'left' : 'right',
  }),
  label: (fromAria) => ({
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 0.5,
    marginBottom: 4,
    fontFamily: 'monospace',
    color: fromAria ? '#60a5fa' : 'rgba(255,255,255,0.9)',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  }),
}

function timeLabel(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function ChatBubble({ message }) {
  const fromAria = message.role === 'aria'

  return (
    <div style={{ ...S.bubble, flexDirection: fromAria ? 'row' : 'row-reverse' }}>
      <div style={S.inner(fromAria)}>
        <div style={S.label(fromAria)}>
          {fromAria && (
             <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#3b82f6', boxShadow: '0 0 8px #3b82f6' }} />
          )}
          {fromAria ? 'ARIA' : 'YOU'}
        </div>
        <div style={S.text(fromAria)}>{message.text}</div>
        <div style={S.time(fromAria)}>{timeLabel(message.ts)}</div>
      </div>
    </div>
  )
}
