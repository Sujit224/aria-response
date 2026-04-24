import asyncio
import json
import os
import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect
from app.models.schemas import IncomingMessage, PipelineState
from app.graph.pipeline import aria_pipeline

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class ConnectionManager:
    """Active WebSocket connections keyed by session_id."""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)

    async def send(self, session_id: str, data: dict):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(session_id)


manager = ConnectionManager()


async def redis_listener(session_id: str, venue_id: str):
    """
    Subscribes to:
      - session:{session_id}    → events targeted at this specific guest/staff
      - staff:{venue_id}        → venue-wide staff alerts (if sender is staff)
      - dashboard:{venue_id}    → ops dashboard events

    Forwards all published messages to the connected WebSocket client.
    """
    r = await aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()

    await pubsub.subscribe(
        f"session:{session_id}",
        f"staff:{venue_id}",
        f"dashboard:{venue_id}",
    )

    try:
        async for raw in pubsub.listen():
            if raw["type"] != "message":
                continue
            try:
                payload = json.loads(raw["data"])
                await manager.send(session_id, payload)
            except Exception:
                continue
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe()
        await r.aclose()


async def chat_ws_endpoint(websocket: WebSocket, session_id: str, venue_id: str):
    """
    Main WebSocket handler.

    Connect:  ws://host/ws/aria/{venue_id}/{session_id}

    Send:
        {
            "session_id": "...",      // optional, resume existing session
            "raw_text": "...",
            "room_id": "poi-uuid",    // guest's room POI id
            "language": "en"
        }

    Receive:  THREAT_DETECTED | CHAT_ACK | STAFF_ALERT | INCIDENT_UPDATE | error
    """
    await manager.connect(session_id, websocket)
    listener_task = asyncio.create_task(redis_listener(session_id, venue_id))

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"event": "error", "data": {"message": "Invalid JSON"}})
                continue

            raw_text = data.get("raw_text", "").strip()
            if not raw_text or raw_text == "__staff_connect__":
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
        listener_task.cancel()
        manager.disconnect(session_id)