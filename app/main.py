import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

import app.db.firebase as firebase
from app.ws.chat import chat_ws_endpoint
from app.api.admin import router as admin_router
from app.api.map import router as map_router
from app.api.incidents import router as incident_router
from app.api.staff import router as staff_router
from app.api.occupants import router as occupants_router
from app.services.ack_watchdog import ack_watchdog
from app.vision.camera_manager import CameraManager

_camera_manager: CameraManager | None = None
_watchdog_task:  asyncio.Task  | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _camera_manager, _watchdog_task

    # 1 — Initialise Firebase (Firestore + FCM) & ThreadPool
    loop = asyncio.get_event_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=50))
    firebase.initialize()
    print("[ARIA] Firebase ready")

    # 2 — Start ack watchdog background task
    _watchdog_task = asyncio.create_task(ack_watchdog())
    print("[ARIA] Ack watchdog started")

    # 3 — Start YOLO camera workers (only if VENUE_ID is set)
    venue_id = os.getenv("VENUE_ID")
    if venue_id:
        _camera_manager = CameraManager(venue_id=venue_id)
        await _camera_manager.start()
    else:
        print("[ARIA] VENUE_ID not set — camera workers skipped")

    yield

    # Shutdown
    if _watchdog_task:
        _watchdog_task.cancel()
    if _camera_manager:
        await _camera_manager.stop()
    print("[ARIA] Shutdown complete")


app = FastAPI(
    title="ARIA — Automated Response and Incident Alerting",
    version="2.0.0",
    description="Firebase-powered emergency response platform with FCM push notifications.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST routers ──────────────────────────────────────────────────
app.include_router(admin_router,     prefix="/api/v1")
app.include_router(map_router,       prefix="/api/v1")
app.include_router(incident_router,  prefix="/api/v1")
app.include_router(staff_router,     prefix="/api/v1")
app.include_router(occupants_router, prefix="/api/v1")


# ── WebSocket ─────────────────────────────────────────────────────
@app.websocket("/ws/aria/{venue_id}/{session_id}")
async def websocket_aria(websocket: WebSocket, venue_id: str, session_id: str):
    """
    Unified real-time channel (Firebase Firestore backed — no Redis).
    Guests connect with their session_id.
    Staff connect with session_id = "staff_{staff_id}".
    """
    await chat_ws_endpoint(websocket, session_id, venue_id)


# ── Health ────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "ARIA", "version": "2.0.0", "backend": "Firebase"}