export const SEV_COLOR = {
  CRITICAL: { bg: '#2e0f12', border: '#ef4444', badge: '#dc2626', text: '#fca5a5', dot: '#ef4444' },
  HIGH:     { bg: '#2e180d', border: '#f97316', badge: '#ea580c', text: '#fdba74', dot: '#f97316' },
  MEDIUM:   { bg: '#291b07', border: '#f59e0b', badge: '#d97706', text: '#fcd34d', dot: '#f59e0b' },
  LOW:      { bg: '#062612', border: '#22c55e', badge: '#16a34a', text: '#86efac', dot: '#22c55e' },
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
  bg:        '#020617', // tailwind slate-950
  bgCard:    '#0f172a', // tailwind slate-900
  bgPanel:   '#1e293b', // tailwind slate-800
  border:    '#1e293b',
  borderHi:  '#334155',
  text:      '#f8fafc',
  textSub:   '#cbd5e1',
  textDim:   '#64748b',
  blue:      '#3b82f6',
  blueGlow:  'rgba(59,130,246,0.15)',
  mono:      "'Space Mono', monospace",
  sans:      "'Inter', system-ui, sans-serif",
}