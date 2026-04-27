import { useState } from 'react'

export function SOSButton({ onSOS, disabled }) {
  const [pressed, setPressed] = useState(false)
  const [countdown, setCountdown] = useState(null)

  function handlePress() {
    if (disabled || pressed) return
    // 3-second hold to confirm — prevents accidental tap
    let count = 3
    setCountdown(count)
    const t = setInterval(() => {
      count--
      setCountdown(count)
      if (count === 0) {
        clearInterval(t)
        setPressed(true)
        setCountdown(null)
        onSOS?.()
      }
    }, 1000)

    // If released early, cancel
    const cancel = () => {
      clearInterval(t)
      setCountdown(null)
      document.removeEventListener('pointerup', cancel)
    }
    document.addEventListener('pointerup', cancel)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <button
        onPointerDown={handlePress}
        disabled={disabled || pressed}
        style={{
          width: 72,
          height: 72,
          borderRadius: '50%',
          border: pressed
            ? '2px solid rgba(220,38,38,0.4)'
            : '2px solid rgba(220,38,38,0.7)',
          background: pressed
            ? 'rgba(220,38,38,0.15)'
            : countdown !== null
            ? 'rgba(220,38,38,0.5)'
            : 'rgba(220,38,38,0.18)',
          color: '#fca5a5',
          fontSize: countdown !== null ? 22 : 11,
          fontFamily: 'monospace',
          fontWeight: 700,
          letterSpacing: countdown !== null ? 0 : 1.5,
          cursor: disabled || pressed ? 'not-allowed' : 'pointer',
          boxShadow: pressed ? 'none' : countdown !== null
            ? '0 0 20px rgba(220,38,38,0.7)'
            : '0 0 14px rgba(220,38,38,0.35)',
          transition: 'all .2s',
          animation: pressed ? 'none' : 'sos-pulse 2s ease-in-out infinite',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          touchAction: 'none',
        }}
      >
        {pressed ? '✓' : countdown !== null ? countdown : 'SOS'}
      </button>
      <span style={{
        fontSize: 9, color: '#64748b', fontFamily: 'monospace',
        letterSpacing: 1, textAlign: 'center', lineHeight: 1.4,
      }}>
        {pressed
          ? 'ALERT SENT'
          : countdown !== null
          ? 'HOLD...'
          : 'HOLD TO ALERT'}
      </span>
      <style>{`
        @keyframes sos-pulse {
          0%,100% { box-shadow: 0 0 14px rgba(220,38,38,0.35); }
          50%      { box-shadow: 0 0 22px rgba(220,38,38,0.55); }
        }
      `}</style>
    </div>
  )
}
