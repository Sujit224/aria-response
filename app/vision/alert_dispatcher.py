"""
app/vision/alert_dispatcher.py
────────────────────────────────
Publishes the THREAT_DETECTED event to Firestore channels
(staff_events + dashboard_events) for all connected WebSocket clients.
"""

from datetime import datetime
from app.vision.pipeline_state import VisionPipelineState
from app.db.collections import (
    save_dispatch,
    publish_staff_event,
    publish_dashboard_event,
)
import uuid


async def vision_alert_dispatcher_node(state: VisionPipelineState) -> VisionPipelineState:
    zone  = state.zone
    alert = state.alert
    if not zone or not alert:
        return state

    ts = datetime.utcnow().isoformat()

    # Dispatch to all staff on floor
    alert_msg = getattr(alert, "description", f"{alert.severity} {alert.type} at {alert.full_location}")
    for staff_id in zone.staff_on_floor:
        await save_dispatch({
            "id":           str(uuid.uuid4()),
            "incident_id":  zone.incident_id,
            "staff_id":     staff_id,
            "message_text": alert_msg,
            "ack_status":   "PENDING",
            "sent_at":      ts,
            "acked_at":     None,
        })

    threat_event = {
        "event": "THREAT_DETECTED",
        "data": {
            "incident_id":   zone.incident_id,
            "type":          alert.type,
            "severity":      alert.severity,
            "zone_name":     alert.zone_name,
            "full_location": alert.full_location,
            "blocked_nodes": alert.blocked_nodes,
            "path_update":   alert.path_update,
            "source":        "vision",
        },
    }

    staff_event = {
        "event": "STAFF_ALERT",
        "data": {
            "incident_id":   zone.incident_id,
            "severity":      alert.severity,
            "threat_type":   alert.type.lower(),
            "full_location": alert.full_location,
            "message":       alert_msg,
            "timestamp":     ts,
            "source":        "vision",
        },
    }

    dashboard_event = {
        "event": "INCIDENT_UPDATE",
        "data": {
            "incident_id":   zone.incident_id,
            "severity":      alert.severity,
            "threat_type":   alert.type.lower(),
            "full_location": alert.full_location,
            "source":        "vision",
            "timestamp":     ts,
        },
    }

    await publish_staff_event(state.venue_id, threat_event)
    await publish_staff_event(state.venue_id, staff_event)
    await publish_dashboard_event(state.venue_id, dashboard_event)

    return state
