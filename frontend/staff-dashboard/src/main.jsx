import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import { Dashboard } from './pages/Dashboard'
import { QRGenerator } from './pages/QRGenerator'

const style = document.createElement('style')
style.textContent = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; background: #050a0f; overflow: hidden; }
  input, button, textarea, select { font-family: inherit; }
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #1e3a5a; border-radius: 2px; }
  ::-webkit-scrollbar-thumb:hover { background: #3b82f6; }
`
document.head.appendChild(style)

function App() {
  const [page, setPage] = useState('dashboard')

  if (page === 'qr') {
    return <QRGenerator onBack={() => setPage('dashboard')} />
  }
  return <Dashboard onGoQR={() => setPage('qr')} />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)