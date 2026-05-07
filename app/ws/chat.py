import asyncio
import json
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from app.models.schemas import IncomingMessage, PipelineState
from app.graph.pipeline import aria_pipeline
from app.db.firebase import get_db


class ConnectionManager:
    """Active WebSocket connections keyed by session_id."""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws

    def disconnect(self, session_id: str, ws: WebSocket):
        if self.active.get(session_id) == ws:
            self.active.pop(session_id, None)

    async def send(self, session_id: str, data: dict):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(session_id, ws)


manager = ConnectionManager()


def _setup_session_listener(session_id: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Attaches a Firestore on_snapshot listener to:
      sessions/{session_id}/events

    When a new event document is added, it is forwarded to the asyncio Queue
    using run_coroutine_threadsafe (because on_snapshot runs in a thread).
    Returns the watch handle (call .unsubscribe() to stop).
    """
    db = get_db()
    events_ref = (
        db.collection("chat_sessions")
        .document(session_id)
        .collection("events")
    )

    start_time = datetime.utcnow().isoformat()

    def _on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == "ADDED":
                data = change.document.to_dict()
                if data.get("_ts", "") >= start_time:
                    asyncio.run_coroutine_threadsafe(queue.put(data), loop)

    return events_ref.on_snapshot(_on_snapshot)


def _setup_staff_listener(venue_id: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Attaches a Firestore on_snapshot listener to:
      venues/{venue_id}/staff_events

    Connected staff WebSocket sessions receive STAFF_ALERT, DISPATCH_REMINDER, etc.
    """
    db = get_db()
    ref = (
        db.collection("venues")
        .document(venue_id)
        .collection("staff_events")
    )

    start_time = datetime.utcnow().isoformat()

    def _on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == "ADDED":
                data = change.document.to_dict()
                if data.get("_ts", "") >= start_time:
                    asyncio.run_coroutine_threadsafe(queue.put(data), loop)

    return ref.on_snapshot(_on_snapshot)


def _setup_dashboard_listener(venue_id: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Attaches a Firestore on_snapshot listener to:
      venues/{venue_id}/dashboard_events
    """
    db = get_db()
    ref = (
        db.collection("venues")
        .document(venue_id)
        .collection("dashboard_events")
    )

    start_time = datetime.utcnow().isoformat()

    def _on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == "ADDED":
                data = change.document.to_dict()
                if data.get("_ts", "") >= start_time:
                    asyncio.run_coroutine_threadsafe(queue.put(data), loop)

    return ref.on_snapshot(_on_snapshot)


async def _queue_forwarder(websocket: WebSocket, queue: asyncio.Queue):
    """
    Continuously drains the asyncio Queue and forwards events to the WebSocket.
    Runs as an asyncio Task alongside the receive loop.
    """
    while True:
        data = await queue.get()
        try:
            await websocket.send_json(data)
        except Exception:
            break


async def chat_ws_endpoint(websocket: WebSocket, session_id: str, venue_id: str):
    """
    Unified real-time WebSocket handler.

    Connect:  ws://host/ws/aria/{venue_id}/{session_id}

    Guest sends:
        { "raw_text": "...", "room_id": "poi-uuid", "language": "en" }

    Staff connects with session_id = "staff_{staff_id}" and receives:
        STAFF_ALERT | DISPATCH_REMINDER | INCIDENT_RESOLVED | PATH_UPDATE

    Events are delivered via Firestore on_snapshot → asyncio Queue → WebSocket.
    No Redis involved.
    """
    await manager.connect(session_id, websocket)
    queue = asyncio.Queue()
    loop  = asyncio.get_event_loop()

    is_staff = session_id.startswith("staff_")

    # ── Attach Firestore listeners ────────────────────────────────
    watches = []
    watches.append(_setup_session_listener(session_id, queue, loop))

    if is_staff:
        watches.append(_setup_staff_listener(venue_id, queue, loop))
        watches.append(_setup_dashboard_listener(venue_id, queue, loop))

    forwarder_task = asyncio.create_task(_queue_forwarder(websocket, queue))

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"event": "error", "data": {"message": "Invalid JSON"}})
                continue

            raw_text = data.get("raw_text", "").strip()
            if not raw_text or raw_text in ("__staff_connect__", "__ping__"):
                continue

            incoming = IncomingMessage(
                session_id = data.get("session_id") or session_id,
                raw_text   = raw_text,
                room_id    = data.get("room_id"),
                venue_id   = venue_id,
                language   = data.get("language", "en"),
            )

            initial_state = PipelineState(incoming=incoming)

            try:
                await aria_pipeline.ainvoke(initial_state)
            except Exception as e:
                await websocket.send_json({
                    "event": "error",
                    "data":  {"message": str(e), "session_id": session_id},
                })

    except WebSocketDisconnect:
        pass
    finally:
        forwarder_task.cancel()
        for watch in watches:
            try:
                watch.unsubscribe()
            except Exception:
                pass
        manager.disconnect(session_id, websocket)