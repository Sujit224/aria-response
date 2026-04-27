const S = {
  bubble: {
    display: 'flex',
    marginBottom: 10,
  },
  inner: (fromAria) => ({
    maxWidth: '82%',
    padding: '10px 14px',
    borderRadius: fromAria ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
    background: fromAria
      ? 'rgba(59,130,246,0.12)'
      : 'rgba(255,255,255,0.06)',
    border: fromAria
      ? '0.5px solid rgba(59,130,246,0.3)'
      : '0.5px solid rgba(255,255,255,0.1)',
    marginLeft:  fromAria ? 0 : 'auto',
    marginRight: fromAria ? 'auto' : 0,
  }),
  text: (fromAria) => ({
    fontSize: 14,
    lineHeight: 1.5,
    color: fromAria ? '#bfdbfe' : '#e2f0ff',
    fontFamily: "'Inter', system-ui, sans-serif",
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  }),
  time: {
    fontSize: 10,
    color: '#475569',
    marginTop: 4,
    fontFamily: 'monospace',
  },
  label: {
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 0.5,
    marginBottom: 3,
    fontFamily: 'monospace',
  },
}

function timeLabel(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function ChatBubble({ message }) {
  const fromAria = message.role === 'aria'

  return (
    <div style={{ ...S.bubble, flexDirection: fromAria ? 'row' : 'row-reverse' }}>
      <div style={S.inner(fromAria)}>
        <div style={{ ...S.label, color: fromAria ? '#60a5fa' : '#94a3b8' }}>
          {fromAria ? 'ARIA' : 'YOU'}
        </div>
        <div style={S.text(fromAria)}>{message.text}</div>
        <div style={S.time}>{timeLabel(message.ts)}</div>
      </div>
    </div>
  )
}
