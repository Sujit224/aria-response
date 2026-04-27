"""
app/vision/zone_resolver.py
────────────────────────────
Resolves which floor / zone a vision threat belongs to,
writes Incident + EmergencyAlert to Firestore,
triggers FCM notifications, and publishes the THREAT_DETECTED event.
"""

import uuid, asyncio
from datetime import datetime
from app.vision.pipeline_state import VisionPipelineState
from app.vision.schemas import VisionZoneResolution, VisionAlertPayload
from app.db.collections import (
    get_floor, get_exits_on_floor,
    get_cameras_on_floor, get_staff_on_floor,
    save_incident, save_emergency_alert,
    publish_staff_event, publish_dashboard_event,
)
from app.services.pathfinding import astar
from app.services.fcm_notifier import send_zone_evacuation_notifications
from app.db.firebase import get_db
import asyncio

SEVERITY_INT = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "NONE": 1}


async def _get_camera_floor(camera_id: str) -> dict | None:
    db = get_db()
    loop = asyncio.get_event_loop()
    doc = await loop.run_in_executor(None, lambda: db.collection("cameras").document(camera_id).get())
    if not doc.exists:
        return None
    cam = doc.to_dict()
    floor = await get_floor(cam["floor_id"])
    return {"camera": cam, "floor": floor}


async def vision_zone_resolver_node(state: VisionPipelineState) -> VisionPipelineState:
    clsf = state.classification
    if not clsf or not clsf.is_threat:
        return state

    ctx = await _get_camera_floor(clsf.camera_id)
    if not ctx:
        state.error = f"Camera {clsf.camera_id} not found in Firestore"
        return state

    camera = ctx["camera"]
    floor  = ctx["floor"]
    floor_id = floor["id"]
    incident_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()

    # Nearest safe exit
    exits = await get_exits_on_floor(floor_id)
    if not exits:
        state.error = "No exits on floor"
        return state

    cam_x, cam_y = camera.get("coord_x", 0), camera.get("coord_y", 0)
    nearest_exit = min(exits, key=lambda e: abs(e["coord_x"] - cam_x) + abs(e["coord_y"] - cam_y))

    path = astar(
        grid    = floor["static_grid"],
        start   = (cam_x, cam_y),
        end     = (nearest_exit["coord_x"], nearest_exit["coord_y"]),
        blocked = [],
    )

    staff_on_floor = await get_staff_on_floor(floor_id, camera["block_id"])
    staff_ids = [s["id"] for s in staff_on_floor]

    full_location = clsf.zone_name or f"Camera zone {clsf.camera_id[:6]}, Floor {floor['level']}"

    # Persist
    sev_int = SEVERITY_INT.get(clsf.severity, 3)
    await save_incident({
        "id":            incident_id,
        "hotel_id":      state.venue_id,
        "floor_id":      floor_id,
        "camera_id":     clsf.camera_id,
        "message_id":    None,
        "origin_poi_id": None,
        "type":          clsf.threat_type,
        "severity":      sev_int,
        "status":        "active",
        "source":        "vision",
        "full_location": full_location,
        "blocked_nodes": [],
        "detected_at":   ts,
    })
    await save_emergency_alert({
        "id":            str(uuid.uuid4()),
        "incident_id":   incident_id,
        "floor_id":      floor_id,
        "blocked_nodes": [],
        "radius":        0.0,
    })

    # FCM push to all guests on floor
    asyncio.create_task(send_zone_evacuation_notifications(
        incident_type = clsf.threat_type,
        severity      = clsf.severity,
        full_location = full_location,
        floor_id      = floor_id,
        floor_level   = floor["level"],
        block_id      = camera["block_id"],
        block_code    = "",
        blocked_nodes = [],
        incident_id   = incident_id,
    ))

    state.zone = VisionZoneResolution(
        incident_id       = incident_id,
        camera_id         = clsf.camera_id,
        floor_id          = floor_id,
        threat_type       = clsf.threat_type,
        severity          = clsf.severity,
        full_location     = full_location,
        blocked_nodes     = [],
        nearest_exit_name = nearest_exit["name"],
        path_to_exit      = [[c[0], c[1]] for c in path],
        staff_on_floor    = staff_ids,
    )

    state.alert = VisionAlertPayload(
        incident_id   = incident_id,
        camera_id     = clsf.camera_id,
        type          = clsf.threat_type.upper(),
        severity      = clsf.severity,
        full_location = full_location,
        zone_name     = nearest_exit["name"],
        blocked_nodes = [],
        path_update   = [[c[0], c[1]] for c in path],
    )
    return state
