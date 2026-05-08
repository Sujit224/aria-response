# ARIA Response
**AI-Driven Emergency Response System for Hospitality**

## 🚀 Overview
ARIA (AI-Driven Response & Incident Awareness) is a next-generation emergency management system designed for large venues like hotels. It bridges the gap between guests in distress, computer vision surveillance, and on-the-ground staff through real-time communication, AI threat analysis, and a 3D situational awareness dashboard.

## ✨ Key Features
- **Guest Emergency PWA**: A fast, installable Progressive Web App allowing guests to instantly report emergencies via text or SOS button, without needing to download a native app.
- **Intelligent Threat Classification**: Uses LangGraph and LLMs (Claude/Groq) to classify natural language chat messages, determine severity, and route alerts.
- **Computer Vision Integration (YOLOv8)**: Analyzes RTSP camera feeds in real-time to detect threats like fire, smoke, and weapons.
- **3D Staff Operations Dashboard**: A React/Three.js dashboard providing a digital twin of the venue, highlighting active incident zones and calculating safe evacuation paths.
- **Real-Time Synchronization**: Powered by WebSockets and Redis Pub/Sub, ensuring staff are alerted the millisecond a threat is classified.
- **Automated Dispatch**: Automatically identifies the closest or most relevant staff member and dispatches them with context.
- **QR Code Onboarding**: Staff can generate dynamic QR codes mapped to specific rooms to allow seamless guest onboarding.

## 🏗️ Architecture
- **Backend**: FastAPI (Python 3.10+), Uvicorn.
- **AI & Vision**: LangGraph, YOLOv8, Groq API (LLMs), OpenCV.
- **Database**: Firebase Firestore (NoSQL for venue data, incidents, staff, guests).
- **Pub/Sub & Websockets**: Redis, FastAPI WebSockets.
- **Frontends**: React, Vite, Three.js (Staff 3D Map), Firebase Cloud Messaging.

## 🛠️ Prerequisites
- Python 3.10+
- Node.js 18+
- Redis Server (running locally or accessible via URI)
- Firebase Project with Firestore enabled (Service Account JSON needed)
- Groq API Key

## ⚙️ Installation & Setup

### 1. Backend Setup
```bash
# Navigate to project root
cd aria-response

# Create and activate virtual environment
python -m venv venv
# On Windows: .\venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
```
*Edit `.env` and add your `GROQ_API_KEY` and path to your Firebase `serviceAccount.json`.*

### 2. Database Seeding
To populate your Firebase Firestore with the digital twin hotel layout and mock data, run:
```bash
python scripts/ingest_hotel.py
python scripts/seed_staff.py
python scripts/seed_occupants.py
```
*Note: `ingest_hotel.py` will output a `VENUE_ID`. Add this to your `.env` files across the backend and frontends.*

### 3. Frontend Setup
You will need to set up two frontend applications.

**Guest PWA:**
```bash
cd frontend/guest-pwa
npm install
cp .env.example .env  # Add your VITE_VENUE_ID and Firebase client config
```

**Staff Dashboard:**
```bash
cd frontend/staff-dashboard
npm install
cp .env.example .env  # Add your VITE_VENUE_ID
```

## 🏃‍♂️ Running the Application

### Option A: Using the Startup Script (Mac/Linux)
```bash
./start_all.sh
```

### Option B: Manual Startup
You will need three terminal windows:

**Terminal 1: Backend**
```bash
# Ensure venv is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2: Guest PWA**
```bash
cd frontend/guest-pwa
npm run dev
# Runs on http://localhost:3000
```

**Terminal 3: Staff Dashboard**
```bash
cd frontend/staff-dashboard
npm run dev
# Runs on http://localhost:3001
```

## 🌐 Deployment (e.g., Railway)
This project is configured to be easily deployed on platforms like Railway.

**Backend Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```
*Tip: Set `FIREBASE_SERVICE_ACCOUNT` as an environment variable containing your full JSON string to avoid committing secure files to your repository.*

**Frontend Environment:**
When deploying the frontends, ensure you set:
- `VITE_API_URL` to your deployed backend URL.
- `VITE_WS_URL` to your deployed backend WebSocket URL.
- `VITE_GUEST_APP_URL` on the Staff Dashboard so room QR codes generate targeting the correct production PWA.

---

## 📁 Directory Structure Reference

```text
aria-response/
├── .env.example
├── .env
├── requirements.txt
├── README.md
├── start_all.sh                            # Local startup script
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
│   │   ├── firebase.py                     # Firebase initialization & get_db
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
│       └── __init__.py                     
│
├── alembic/                                # DB migrations
│
├── frontend/
│   ├── guest-pwa/                          # Guest emergency chat (installable PWA)
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   └── src/
│   │       ├── main.jsx
│   │       ├── hooks/useARIASocket.js      # WebSocket hook with auto-reconnect
│   │       ├── components/                 # SOSButton, AlertBanner, ChatBubble
│   │       └── pages/GuestChat.jsx         # Main PWA screen
│   │
│   └── staff-dashboard/                    # Staff ops dashboard
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── main.jsx
│           ├── hooks/useStaffSocket.js     # Staff WebSocket hook
│           ├── components/                 # IncidentCard, FloorMap, DispatchLog, 3D Views
│           └── pages/
│               ├── Dashboard.jsx           # Main page: live feed + detail panel
│               ├── Hotel3D.jsx             # Embedded 3D hotel navigator
│               └── QRGenerator.jsx         # Room QR Code Generator
│
├── scripts/                                # Database seeding and dev scripts
│   ├── ingest_hotel.py
│   ├── seed_staff.py
│   └── seed_occupants.py
│
└── public/                                 # Static assets
```
