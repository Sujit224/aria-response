import React, { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { TopBar } from '../components/TopBar'
import { T } from '../lib/constants'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const VENUE_ID = import.meta.env.VITE_VENUE_ID || new URLSearchParams(location.search).get('venue') || 'auto'

export function QRGenerator({ onBack }) {
  const [rooms, setRooms] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchRooms() {
      try {
        const res = await fetch(`${API}/map/pois?type=room&limit=200`)
        if (!res.ok) throw new Error('Failed to fetch')
        const data = await res.json()
        setRooms(data.filter(p => p.type === 'room'))
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchRooms()
  }, [])

  const guestAppUrl = import.meta.env.VITE_GUEST_APP_URL || window.location.origin.replace('3001', '3000')

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', background: T.bg,
      color: T.text, fontFamily: T.sans,
      overflow: 'hidden',
    }}>
      {/* Basic header similar to TopBar but just for navigation */}
      <div style={{
        height: 60,
        background: 'rgba(5, 10, 15, 0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16,
        zIndex: 100,
      }}>
        <button 
          onClick={onBack}
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#cbd5e1', borderRadius: 8,
            padding: '8px 16px', fontSize: 11,
            fontFamily: T.mono, fontWeight: 600,
            cursor: 'pointer', letterSpacing: 1,
            transition: 'all 0.2s',
          }}
          onMouseOver={e => e.target.style.background = 'rgba(255, 255, 255, 0.08)'}
          onMouseOut={e => e.target.style.background = 'rgba(255, 255, 255, 0.03)'}
        >
          ← BACK TO DASHBOARD
        </button>
        <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: 1, color: '#f8fafc' }}>
          ROOM QR CODES
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
        <p style={{ marginBottom: 32, color: T.textDim, fontSize: 14, maxWidth: 600 }}>
          Print these QR codes and place them in the respective rooms. Guests can scan them to seamlessly access the ARIA Emergency Chat system without downloading an app.
        </p>

        {loading ? (
          <div style={{ color: T.textDim, fontFamily: T.mono, fontSize: 12 }}>LOADING ROOMS...</div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 24
          }}>
            {rooms.map(room => {
              const url = `${guestAppUrl}?venue=${VENUE_ID}&room=${room.id}`
              
              return (
                <div key={room.id} style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: 16, padding: 24,
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
                  transition: 'transform 0.2s',
                }}
                onMouseOver={e => e.currentTarget.style.transform = 'translateY(-4px)'}
                onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}
                >
                  <div style={{
                    background: '#fff',
                    padding: 12,
                    borderRadius: 12,
                    marginBottom: 16,
                  }}>
                    <QRCodeSVG 
                      value={url} 
                      size={140} 
                      level={"M"}
                      includeMargin={false}
                    />
                  </div>
                  <div style={{
                    color: T.text, fontWeight: 600,
                    fontSize: 16, fontFamily: T.sans, letterSpacing: 0.5,
                  }}>
                    {room.name}
                  </div>
                  <div style={{
                    color: T.textDim, fontSize: 11, marginTop: 6, fontFamily: T.mono,
                    wordBreak: 'break-all', textAlign: 'center', letterSpacing: 1
                  }}>
                    ID: {room.id}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
