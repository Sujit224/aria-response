"""
app/vision/aria_bridge.py
──────────────────────────
Bridges the standalone vision detector (app/vision/main.py) into the
ARIA backend pipeline so alerts show up in the Staff Dashboard in real-time.

When the standalone ThreatAgent produces a valid alert it calls
`ARIABridge.dispatch()` which:
  1. Saves an incident document to Firestore
  2. Publishes THREAT_DETECTED + INCIDENT_UPDATE to dashboard_events
  3. Publishes STAFF_ALERT to staff_events
  → All connected WebSocket clients (staff dashboard) receive the events
    via their on_snapshot Firestore listeners.

Fixed defaults used when the standalone detector has no venue context:
  VENUE_ID  → from .env (VENUE_ID)
  ROOM_ID   → Room 314 (Block C, Floor 3) — the canonical test room
"""

import os
import asyncio
import uuid
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import app.db.firebase as firebase

# ─── Severity mapping (standalone detector priorities → ARIA severities) ───
_SEVERITY_MAP = {
    "CRITICAL": "CRITICAL",
    "HIGH":     "HIGH",
    "MEDIUM":   "MEDIUM",
    "LOW":      "LOW",
    "INVALID":  "LOW",
}

# ─── Detector source → ARIA threat_type ────────────────────────────────────
_TYPE_MAP = {
    "weapon_detector": "security",
    "smoke_detector":  "fire",
    "bag_detector":    "security",
    "scan_detector":   "security",
}

# ─── Default venue / room context ──────────────────────────────────────────
DEFAULT_VENUE_ID = os.getenv("VENUE_ID", "d6d3d153-5b43-478f-8805-f46ac29abea3")
DEFAULT_ROOM_ID  = "2f92b9fd-dd53-4792-8294-8bababadd0aa"   # Room 214
DEFAULT_ROOM_NAME = "Room 214"


class ARIABridge:
    """
    Thread-safe bridge between the standalone vision detector and the ARIA
    Firestore pipeline.  Call `dispatch()` from the AlertProcessor thread;
    it creates its own event-loop so it doesn't block the detection loop.
    """

    def __init__(self):
        self._initialized = False
        self._loop = None

    def _ensure_firebase(self):
        if not self._initialized:
            firebase.initialize()
            self._initialized = True

    def _calculate_blocked_nodes(self, location_str: str, base_x: int, base_y: int) -> list:
        """Translate vision region string (e.g. 'Top-Left') into grid coordinates."""
        nodes = []
        offset_x = 0
        offset_y = 0

        # Adjust center based on the relative quadrant detected by YOLO
        if "Left" in location_str:   offset_x = -4
        if "Right" in location_str:  offset_x = 4
        if "Top" in location_str:    offset_y = -3
        if "Bottom" in location_str: offset_y = 3

        cx = max(2, min(21, base_x + offset_x))
        cy = max(2, min(9,  base_y + offset_y))

        # Create a 3x3 cluster of blocked nodes
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nodes.append({"x": cx + dx, "y": cy + dy})
        return nodes

    def dispatch(self, alert: dict, threat_result: dict):
        """
        Called synchronously from the AlertProcessor background thread.
        Runs the async Firestore writes in a new event loop (thread-safe).
        """
        self._ensure_firebase()
        try:
            # Create a new event loop for this thread call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._publish(alert, threat_result))
            loop.close()
        except Exception as e:
            print(f"  [ARIABridge] WARN: Dispatch failed: {e}")

    async def _publish(self, alert: dict, threat_result: dict):
        """Write incident + events to Firestore."""
        from app.db.firebase import get_db

        db         = get_db()
        # ── Setup metadata ───────────────────────────────────────────────
        ts = datetime.utcnow().isoformat() + "Z"
        loop       = asyncio.get_event_loop()
        incident_id = str(uuid.uuid4())

        venue_id   = DEFAULT_VENUE_ID
        room_id    = DEFAULT_ROOM_ID
        room_name  = DEFAULT_ROOM_NAME
        source_str = alert.get("source", "weapon_detector")
        det_type   = alert.get("type", "UNKNOWN")
        location   = alert.get("location", "Unknown")
        severity   = _SEVERITY_MAP.get(threat_result.get("threat_level", "HIGH"), "HIGH")
        threat_type = _TYPE_MAP.get(source_str, "security")

        # ── Look up floor, block and coords from camera Firestore doc ──────
        cam_id = alert.get("camera_id", "test-cam-001")
        cam_doc_ref = db.collection("cameras").document(cam_id)
        cam_snap = await loop.run_in_executor(None, cam_doc_ref.get)
        cam_data = cam_snap.to_dict() if cam_snap.exists else {}
        
        floor_id_for_incident = cam_data.get("floor_id", "")
        block_id_for_incident = cam_data.get("block_id", "")
        base_x = cam_data.get("coord_x", 12)
        base_y = cam_data.get("coord_y", 6)

        # Enrich with real block/floor names
        block_code = "C"
        floor_level = "2"
        if block_id_for_incident:
            b_snap = await loop.run_in_executor(None, db.collection("blocks").document(block_id_for_incident).get)
            if b_snap.exists: block_code = b_snap.to_dict().get("block_code", "C")
        if floor_id_for_incident:
            f_snap = await loop.run_in_executor(None, db.collection("floors").document(floor_id_for_incident).get)
            if f_snap.exists: floor_level = str(f_snap.to_dict().get("level", "2"))

        # Format descriptive location string
        cam_label = cam_id.replace("test-cam-", "CAM-").upper()
        full_location = f"{cam_label} | Block {block_code} | Floor {floor_level} | {room_name} — {location}"
        
        discovery_time = datetime.now().strftime("%H:%M:%S")
        message    = threat_result.get("threat_message", f"{det_type} detected at {full_location}")
        # Ensure discovery time is prominently appended
        if discovery_time not in message:
            message = f"{message} [Discovered: {discovery_time}]"

        base_x = cam_data.get("coord_x", 12)
        base_y = cam_data.get("coord_y", 6)

        # ── Calculate blocked nodes for map highlighting ──
        # Returns list of {"x":, "y":}
        raw_blocked = self._calculate_blocked_nodes(location, base_x, base_y)
        # Format for WebSocket payload [[x,y], ...]
        blocked_nodes = [[n["x"], n["y"]] for n in raw_blocked]

        from app.db.collections import _flatten_arrays

        # ── 1. Save incident document ────────────────────────────────────
        incident_doc = {
            "id":           incident_id,
            "hotel_id":     venue_id,
            "room_id":      room_id,
            "room_name":    room_name,
            "floor_id":     floor_id_for_incident,
            "type":         threat_type,
            "severity":     severity,
            "status":       "active",
            "source":       "vision",
            "full_location": full_location,
            "description":  message,
            "blocked_nodes": blocked_nodes,
            "assigned_staff_names": [],
            "created_at":   ts,
            "detected_at":  ts,
            "updated_at":   ts,
            "_ts":          ts,
        }
        await loop.run_in_executor(
            None,
            lambda: db.collection("incidents").document(incident_id).set(_flatten_arrays(incident_doc))
        )

        # ── 2. Payload for dashboard & staff events ──────────────────────
        base_data = {
            "incident_id":   incident_id,
            "type":          threat_type,
            "severity":      severity,
            "room_id":       room_id,
            "floor_id":      floor_id_for_incident,
            "full_location": full_location,
            "description":   message,
            "blocked_nodes": blocked_nodes,
            "detected_at":   ts,
            "source":        "vision",
            "_ts":           ts,
        }

        threat_event = {
            "event": "THREAT_DETECTED",
            "data":  base_data,
            "_ts":   ts,
        }

        staff_event = {
            "event": "STAFF_ALERT",
            "data":  {**base_data, "message": f"ALERT: {message}"},
            "_ts":   ts,
        }

        dashboard_event = {
            "event": "INCIDENT_UPDATE",
            "data":  base_data,
            "_ts":   ts,
        }

        # ── 3. Publish to Firestore realtime channels ────────────────────
        ev_ref = (
            db.collection("venues")
              .document(venue_id)
              .collection("staff_events")
        )
        dash_ref = (
            db.collection("venues")
              .document(venue_id)
              .collection("dashboard_events")
        )

        await loop.run_in_executor(None, lambda: ev_ref.add(_flatten_arrays({**threat_event})))
        await loop.run_in_executor(None, lambda: ev_ref.add(_flatten_arrays({**staff_event})))
        await loop.run_in_executor(None, lambda: dash_ref.add(_flatten_arrays({**dashboard_event})))

        print(f"  [ARIABridge] OK: Alert published -> Firestore | incident={incident_id[:8]}...")
        print(f"  [ARIABridge]    {severity} {det_type} at {full_location}")
