import React from 'react'
import ReactDOM from 'react-dom/client'
import { GuestChat } from './pages/GuestChat'

// Global styles
const style = document.createElement('style')
style.textContent = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; background: #050a0f; overflow: hidden; }
  #root      { height: 100%; display: flex; flex-direction: column; }
  input, button, textarea, select { font-family: inherit; }

  /* Scrollbars */
  ::-webkit-scrollbar        { width: 3px; height: 3px; }
  ::-webkit-scrollbar-track  { background: transparent; }
  ::-webkit-scrollbar-thumb  { background: #1e3a5a; border-radius: 2px; }

  /* Safe area insets (iPhone notch / dynamic island) */
  body { padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom); }
`
document.head.appendChild(style)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GuestChat />
  </React.StrictMode>
)
