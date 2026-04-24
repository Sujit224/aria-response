import os
import json
from datetime import datetime
from sqlalchemy import select
import redis.asyncio as aioredis
from app.models.schemas import PipelineState
from app.models.tables import Dispatch, Staff
from app.db.session import AsyncSessionLocal

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


async def _redis():
    return await aioredis.from_url(REDIS_URL, decode_responses=True)


async def alert_dispatcher_node(state: PipelineState) -> PipelineState:
    """
    1. Writes a Dispatch row for each zone-1 staff member
    2. Publishes THREAT_DETECTED to venue dashboard channel
    3. Publishes STAFF_DISPATCHED to the guest's session channel
    4. Publishes staff alert to staff channel
    """
    zone = state.zone
    msgs = state.messages

    # ── Dispatch rows for zone 1 staff ───────────────────────────
    async with AsyncSessionLocal() as db:
        for staff_id in zone.staff_on_floor:
            staff_res = await db.execute(select(Staff).where(Staff.id == staff_id))
            staff = staff_res.scalar_one_or_none()
            dispatch = Dispatch(
                incident_id  = zone.incident_id,
                staff_id     = staff_id,
                message_text = msgs.msg_staff_zone1,
                ack_status   = "PENDING",
            )
            db.add(dispatch)
        await db.commit()

    # ── Build WebSocket event payloads ────────────────────────────
    blocked_list = [[c.x, c.y] for c in zone.blocked_nodes]
    path_list    = [[c.x, c.y] for c in zone.evacuation_path]

    threat_event = {
        "event": "THREAT_DETECTED",
        "data": {
            "incident_id":   zone.incident_id,
            "type":          zone.threat_type.upper(),
            "severity":      zone.severity,
            "zone_name":     zone.nearest_exit_name,
            "full_location": zone.full_location,
            "blocked_nodes": blocked_list,
            "path_update":   path_list,
        },
    }

    staff_event = {
        "event": "STAFF_ALERT",
        "data": {
            "incident_id":    zone.incident_id,
            "severity":       zone.severity,
            "threat_type":    zone.threat_type,
            "full_location":  zone.full_location,
            "zone1_msg":      msgs.msg_staff_zone1,
            "zone2_msg":      msgs.msg_staff_zone2,
            "zone3_msg":      msgs.msg_staff_zone3,
            "suggested_actions": msgs.suggested_actions,
            "timestamp":      datetime.utcnow().isoformat(),
        },
    }

    guest_ack_event = {
        "event": "CHAT_ACK",
        "data": {
            "incident_id": zone.incident_id,
            "message":     msgs.msg_guest_ack,
            "severity":    zone.severity,
        },
    }

    dashboard_event = {
        "event": "INCIDENT_UPDATE",
        "data": {
            "incident_id":   zone.incident_id,
            "summary":       msgs.dashboard_summary,
            "severity":      zone.severity,
            "threat_type":   zone.threat_type,
            "full_location": zone.full_location,
            "source":        "chat",
            "timestamp":     datetime.utcnow().isoformat(),
        },
    }

    # ── Publish to Redis channels ─────────────────────────────────
    try:
        r = await _redis()
        # Guest gets THREAT_DETECTED (includes path) + their personal ack
        await r.publish(f"session:{zone.session_id}", json.dumps(threat_event))
        await r.publish(f"session:{zone.session_id}", json.dumps(guest_ack_event))
        # Staff channel (all connected staff for this venue)
        await r.publish(f"staff:{zone.venue_id}", json.dumps(staff_event))
        # Dashboard
        await r.publish(f"dashboard:{zone.venue_id}", json.dumps(dashboard_event))
        await r.aclose()
    except Exception as e:
        print(f"[ARIA] Redis publish failed: {e}")

    return state


async def normal_reply_node(state: PipelineState) -> PipelineState:
    """Non-threat message: send a friendly reply back to the guest only."""
    enriched = state.enriched
    try:
        r = await _redis()
        await r.publish(
            f"session:{enriched.session_id}",
            json.dumps({
                "event": "CHAT_ACK",
                "data": {
                    "message": "Thank you for reaching out. How can we help you?",
                    "session_id": enriched.session_id,
                },
            }),
        )
        await r.aclose()
    except Exception as e:
        print(f"[ARIA] Redis publish failed (normal reply): {e}")
    return state