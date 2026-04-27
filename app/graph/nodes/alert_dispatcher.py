import uuid
from datetime import datetime
from app.models.schemas import PipelineState
from app.db.collections import (
    save_dispatch,
    publish_session_event,
    publish_staff_event,
    publish_dashboard_event,
)


async def alert_dispatcher_node(state: PipelineState) -> PipelineState:
    """
    1. Writes a Dispatch document for each zone-1 staff member in Firestore
    2. Publishes THREAT_DETECTED to guest's session event channel (Firestore)
    3. Publishes STAFF_ALERT to venue staff channel (Firestore)
    4. Publishes INCIDENT_UPDATE to dashboard channel (Firestore)

    All real-time delivery is done via Firestore on_snapshot in ws/chat.py.
    Redis has been fully removed.
    """
    zone = state.zone
    msgs = state.messages
    ts   = datetime.utcnow().isoformat()

    # ── Dispatch rows for zone 1 staff ───────────────────────────
    for staff_id in zone.staff_on_floor:
        await save_dispatch({
            "id":           str(uuid.uuid4()),
            "incident_id":  zone.incident_id,
            "staff_id":     staff_id,
            "message_text": msgs.msg_staff_zone1,
            "ack_status":   "PENDING",
            "sent_at":      ts,
            "acked_at":     None,
        })

    # ── Build event payloads ──────────────────────────────────────
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
            "assigned_staff_names": zone.assigned_staff_names,
            "static_grid":   zone.static_grid,
            "grid_width":    zone.grid_width,
            "grid_height":   zone.grid_height,
            "guest_coord":   [zone.guest_coord.x, zone.guest_coord.y],
            "exit_coord":    [zone.nearest_exit_coord.x, zone.nearest_exit_coord.y],
            "all_pois":      zone.all_pois,
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
            "timestamp":      ts,
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
            "timestamp":     ts,
        },
    }

    # ── Publish to Firestore channels (replaces Redis pub/sub) ────
    await publish_session_event(zone.session_id, threat_event)
    await publish_session_event(zone.session_id, guest_ack_event)
    await publish_staff_event(zone.venue_id, staff_event)
    await publish_dashboard_event(zone.venue_id, dashboard_event)

    return state


async def normal_reply_node(state: PipelineState) -> PipelineState:
    """Non-threat message — publishes a friendly CHAT_ACK to the guest's session channel."""
    enriched = state.enriched
    await publish_session_event(
        enriched.session_id,
        {
            "event": "CHAT_ACK",
            "data": {
                "message":    "Thank you for reaching out. How can we assist you?",
                "session_id": enriched.session_id,
            },
        },
    )
    return state