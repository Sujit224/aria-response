/**
 * WebGLErrorBoundary.jsx
 * ────────────────────────
 * Catches WebGL / Three.js render errors and shows a 2D fallback grid
 * instead of crashing the entire IncidentDetail panel.
 */
import { Component } from 'react'
import { T } from '../lib/constants'

export class WebGLErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.warn('[CameraView3D] WebGL error caught:', error.message)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          height: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: '#020810', borderRadius: 10,
          border: '1px solid #1e3a5f', gap: 12,
        }}>
          <div style={{ fontSize: 28 }}>🎥</div>
          <div style={{ fontSize: 12, color: '#3b82f6', fontFamily: 'monospace', letterSpacing: 2 }}>
            3D VIEW UNAVAILABLE
          </div>
          <div style={{ fontSize: 10, color: '#475569', fontFamily: 'monospace', textAlign: 'center', maxWidth: 260 }}>
            WebGL is not supported in this environment.
            <br />Camera coverage data is still being monitored.
          </div>
          {this.props.floorId && (
            <div style={{ fontSize: 10, color: '#1e40af', fontFamily: 'monospace', marginTop: 8 }}>
              FLOOR ID: {this.props.floorId?.slice(0, 18)}...
            </div>
          )}
        </div>
      )
    }
    return this.props.children
  }
}
