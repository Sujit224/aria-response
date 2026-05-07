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
        loop       = asyncio.get_event_loop()
        ts         = datetime.utcnow().isoformat()
        incident_id = str(uuid.uuid4())

        venue_id   = DEFAULT_VENUE_ID
        room_id    = DEFAULT_ROOM_ID
        room_name  = DEFAULT_ROOM_NAME
        source_str = alert.get("source", "weapon_detector")
        det_type   = alert.get("type", "UNKNOWN")
        location   = alert.get("location", "Unknown")
        severity   = _SEVERITY_MAP.get(threat_result.get("threat_level", "HIGH"), "HIGH")
        threat_type = _TYPE_MAP.get(source_str, "security")
        full_location = f"{room_name} — {location}"
        message    = threat_result.get("threat_message",
                     f"{det_type} detected at {full_location}")

        # ── Look up floor_id from camera Firestore doc ────────────────────
        cam_doc_ref = db.collection("cameras").document("test-cam-001")
        cam_snap = await loop.run_in_executor(None, cam_doc_ref.get)
        cam_data = cam_snap.to_dict() if cam_snap.exists else {}
        floor_id_for_incident = cam_data.get("floor_id", "")

        # ── 1. Save incident document ────────────────────────────────────
        incident_doc = {
            "id":           incident_id,
            "hotel_id":     venue_id,
            "room_id":      room_id,
            "room_name":    room_name,
            "floor_id":     floor_id_for_incident,
            "type":         threat_type,
            "severity":     severity,
            "status":       "ACTIVE",
            "source":       "vision",
            "description":  message,
            "assigned_staff_names": [],
            "created_at":   ts,
            "updated_at":   ts,
            "_ts":          ts,
        }
        await loop.run_in_executor(
            None,
            lambda: db.collection("incidents").document(incident_id).set(incident_doc)
        )

        # ── 2. Payload for dashboard & staff events ──────────────────────
        threat_event = {
            "_ts":   ts,
            "event": "THREAT_DETECTED",
            "data": {
                "incident_id":   incident_id,
                "type":          det_type,
                "severity":      severity,
                "zone_name":     room_name,
                "full_location": full_location,
                "floor_id":      floor_id_for_incident,
                "blocked_nodes": [],
                "path_update":   [],
                "source":        "vision",
                "room_id":       room_id,
                "message":       message,
            },
        }

        staff_event = {
            "_ts":   ts,
            "event": "STAFF_ALERT",
            "data": {
                "incident_id":   incident_id,
                "severity":      severity,
                "threat_type":   threat_type,
                "full_location": full_location,
                "message":       message,
                "timestamp":     ts,
                "source":        "vision",
                "camera_source": source_str,
                "detection":     det_type,
            },
        }

        dashboard_event = {
            "_ts":   ts,
            "event": "INCIDENT_UPDATE",
            "data": {
                "incident_id":   incident_id,
                "severity":      severity,
                "threat_type":   threat_type,
                "full_location": full_location,
                "source":        "vision",
                "timestamp":     ts,
                "status":        "ACTIVE",
            },
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

        await loop.run_in_executor(None, lambda: ev_ref.add({**threat_event}))
        await loop.run_in_executor(None, lambda: ev_ref.add({**staff_event}))
        await loop.run_in_executor(None, lambda: dash_ref.add({**dashboard_event}))

        print(f"  [ARIABridge] OK: Alert published -> Firestore | incident={incident_id[:8]}...")
        print(f"  [ARIABridge]    {severity} {det_type} at {full_location}")
