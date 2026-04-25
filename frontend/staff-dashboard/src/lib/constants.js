export const SEV_COLOR = {
  CRITICAL: { bg: '#450a0a', border: '#dc2626', badge: '#dc2626', text: '#fca5a5', dot: '#dc2626' },
  HIGH:     { bg: '#431407', border: '#ea580c', badge: '#ea580c', text: '#fdba74', dot: '#ea580c' },
  MEDIUM:   { bg: '#422006', border: '#d97706', badge: '#d97706', text: '#fcd34d', dot: '#d97706' },
  LOW:      { bg: '#052e16', border: '#16a34a', badge: '#16a34a', text: '#86efac', dot: '#16a34a' },
}

// severity integer (1-5) → label
export const SEV_LABEL = { 5: 'CRITICAL', 4: 'HIGH', 3: 'MEDIUM', 2: 'LOW', 1: 'LOW' }

export const THREAT_ICON = {
  medical:  '✚',
  fire:     '🔥',
  security: '⚠',
  crowd:    '⬡',
}

export const THREAT_LABEL = {
  medical:  'Medical Emergency',
  fire:     'Fire / Smoke',
  security: 'Security Threat',
  crowd:    'Crowd Incident',
}

export const ACK_COLOR = {
  PENDING:     '#f59e0b',
  ACCEPTED:    '#3b82f6',
  ON_SCENE:    '#22c55e',
}

// CSS-in-JS base tokens
export const T = {
  bg:        '#050a0f',
  bgCard:    '#090f1a',
  bgPanel:   '#0a1220',
  border:    'rgba(59,130,246,0.18)',
  borderHi:  'rgba(59,130,246,0.45)',
  text:      '#e2f0ff',
  textSub:   '#94a3b8',
  textDim:   '#475569',
  blue:      '#3b82f6',
  blueGlow:  'rgba(59,130,246,0.15)',
  mono:      "'Space Mono', monospace",
  sans:      "'Inter', system-ui, sans-serif",
}