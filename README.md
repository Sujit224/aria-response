# aria-response

## Directory Structure Reference

```text
aria-response/
├── .env.example
├── .env
├── requirements.txt
├── README.md
│
├── app/                                    # FastAPI backend
│   ├── __init__.py
│   ├── main.py                             # Entry point, lifespan, routes mount
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                       # REST: incidents, ack, session history
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py                      # Async engine, get_db, init_db
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tables.py                       # SQLAlchemy: all 12 DB tables
│   │   └── schemas.py                      # Pydantic: PipelineState + all payloads
│   │
│   ├── graph/                              # Chat detection LangGraph pipeline
│   │   ├── __init__.py
│   │   ├── pipeline.py                     # Graph wiring + conditional routing
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── enricher.py                 # Attach room/block/floor from guest profile
│   │       ├── nlp_classifier.py           # Claude-powered threat classification
│   │       ├── zone_resolver.py            # Map to zones 1/2/3, persist Incident
│   │       ├── llm_responder.py            # Generate all role-specific messages
│   │       └── alert_dispatcher.py         # Redis pub/sub + DB dispatch logs
│   │
│   ├── vision/                             # YOLO detection pipeline
│   │   ├── __init__.py
│   │   ├── schemas.py                      # YOLODetection, ThreatEvent, ContextFilterResult
│   │   ├── pipeline_state.py               # VisionPipelineState
│   │   ├── pipeline.py                     # Vision LangGraph graph
│   │   ├── camera_worker.py                # RTSP reader, YOLOv8 inference, per-frame logic
│   │   ├── camera_manager.py               # Loads all active cameras, spins up workers
│   │   ├── context_filter.py               # Guard post suppression + SuppressionLog
│   │   ├── threat_classifier.py            # YOLO class → ThreatEvent + severity
│   │   ├── zone_resolver.py                # Vision-path zone resolver node
│   │   └── llm_responder.py                # Vision-path LLM responder node
│   │
│   ├── ws/
│   │   ├── __init__.py
│   │   └── chat.py                         # WebSocket handler + Redis listener
│   │
│   └── services/
│       └── __init__.py                     # (reserved: ack watchdog, push notify)
│
├── alembic/                                # DB migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
│
├── frontend/
│   │
│   ├── guest-pwa/                          # Guest emergency chat (installable PWA)
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── index.html
│   │   ├── public/
│   │   │   ├── icon-192.png
│   │   │   └── icon-512.png
│   │   └── src/
│   │       ├── main.jsx
│   │       ├── hooks/
│   │       │   └── useARIASocket.js        # WebSocket hook with auto-reconnect
│   │       ├── lib/
│   │       │   └── session.js              # Session/guest ID helpers, getVenueId
│   │       ├── components/
│   │       │   ├── SOSButton.jsx           # One-tap panic button
│   │       │   ├── AlertBanner.jsx         # Severity-colored alert overlay
│   │       │   ├── ChatBubble.jsx          # Message thread bubble
│   │       │   └── StatusBar.jsx           # Connection status + room location
│   │       └── pages/
│   │           └── GuestChat.jsx           # Main PWA screen
│   │
│   └── staff-dashboard/                    # Staff ops dashboard
│       ├── package.json
│       ├── vite.config.js
│       ├── index.html
│       └── src/
│           ├── main.jsx
│           ├── hooks/
│           │   └── useStaffSocket.js       # Staff WebSocket hook
│           ├── lib/
│           │   └── api.js                  # REST client: incidents, resolve, ack
│           ├── components/
│           │   ├── IncidentCard.jsx        # Severity-colored incident list card
│           │   ├── IncidentDetail.jsx      # Zone map, dispatch log, resolve button
│           │   ├── FloorMap.jsx            # SVG zone 1/2/3 visualizer
│           │   ├── DispatchLog.jsx         # Per-incident ack tracking table
│           │   └── StatusBar.jsx           # Live connection + venue status
│           └── pages/
│               ├── Dashboard.jsx           # Main page: live feed + detail panel
│               └── Hotel3D.jsx             # Embedded 3D hotel navigator
│
└── public/
    └── hotel3d.html                        # Standalone 3D hotel navigator (Three.js)
```
