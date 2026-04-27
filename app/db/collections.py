"""
Async Firestore helpers for every collection in the ARIA data model.

All functions are async and use asyncio.get_event_loop().run_in_executor
so the synchronous firebase-admin SDK never blocks the event loop.

Collection layout
─────────────────
hotels/{hotel_id}
blocks/{block_id}
floors/{floor_id}
pois/{poi_id}
cameras/{camera_id}
  └─ coverage_zones/{zone_id}   (subcollection)
guard_posts/{post_id}
suppression_logs/{log_id}
staff/{staff_id}
room_occupants/{room_id}        ← NEW: current guests + FCM tokens
guests/{guest_id}
chat_sessions/{session_id}
  └─ events/{event_id}          ← real-time event stream (replaces Redis)
chat_messages/{message_id}
incidents/{incident_id}
emergency_alerts/{alert_id}
dispatches/{dispatch_id}
venues/{venue_id}/staff_events/{event_id}      ← staff broadcast channel
venues/{venue_id}/dashboard_events/{event_id}  ← dashboard broadcast channel
"""

import json
import asyncio
import uuid
from datetime import datetime
from typing import Any
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from app.db.firebase import get_db

def _flatten_arrays(d: dict):
    """Firestore does not support nested arrays. Serialize them as JSON strings."""
    if not isinstance(d, dict): return d
    res = {}
    for k, v in d.items():
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
            res[k] = json.dumps(v)
        elif isinstance(v, dict):
            res[k] = _flatten_arrays(v)
        else:
            res[k] = v
    return res

def _unflatten_arrays(d: dict):
    """Deserialize JSON strings back to nested arrays."""
    if not d: return d
    res = {}
    for k, v in d.items():
        if isinstance(v, str) and v.startswith("[") and v.endswith("]") and "[[" in v:
            try:
                res[k] = json.loads(v)
            except Exception:
                res[k] = v
        elif isinstance(v, dict):
            res[k] = _unflatten_arrays(v)
        else:
            res[k] = v
    return res
from app.db.firebase import get_db


def _now() -> str:
    return datetime.utcnow().isoformat()


def _id() -> str:
    return str(uuid.uuid4())


async def _run(fn):
    """Run a sync Firestore call in the default thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn)


# ──────────────────────────────────────────────────────────────────
# ARCHITECTURE / DIGITAL TWIN
# ──────────────────────────────────────────────────────────────────

async def save_hotel(name: str, address: str) -> str:
    doc_id = _id()
    db = get_db()
    await _run(lambda: db.collection("hotels").document(doc_id).set(_flatten_arrays({
        "id": doc_id, "name": name, "address": address,
        "created_at": _now(),
    })))
    return doc_id


async def get_hotel(hotel_id: str) -> dict | None:
    db = get_db()
    doc = await _run(lambda: db.collection("hotels").document(hotel_id).get())
    return _unflatten_arrays(doc.to_dict()) if doc.exists else None


async def list_hotels() -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(db.collection("hotels").stream()))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def save_block(hotel_id: str, name: str, block_code: str) -> str:
    doc_id = _id()
    db = get_db()
    await _run(lambda: db.collection("blocks").document(doc_id).set(_flatten_arrays({
        "id": doc_id, "hotel_id": hotel_id,
        "name": name, "block_code": block_code,
    })))
    return doc_id


async def list_blocks(hotel_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("blocks").where("hotel_id", "==", hotel_id).stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def get_block(block_id: str) -> dict | None:
    db = get_db()
    doc = await _run(lambda: db.collection("blocks").document(block_id).get())
    return _unflatten_arrays(doc.to_dict()) if doc.exists else None


async def save_floor(block_id: str, level: int, grid_width: int,
                     grid_height: int, static_grid: list) -> str:
    doc_id = _id()
    db = get_db()
    await _run(lambda: db.collection("floors").document(doc_id).set(_flatten_arrays({
        "id": doc_id, "block_id": block_id, "level": level,
        "grid_width": grid_width, "grid_height": grid_height,
        "static_grid": static_grid,
    })))
    return doc_id


async def get_floor(floor_id: str) -> dict | None:
    db = get_db()
    doc = await _run(lambda: db.collection("floors").document(floor_id).get())
    return _unflatten_arrays(doc.to_dict()) if doc.exists else None


async def list_floors(block_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("floors").where("block_id", "==", block_id)
        .order_by("level").stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def save_poi(floor_id: str, name: str, type_: str,
                   coord_x: int, coord_y: int, is_safe_exit: bool = False) -> str:
    doc_id = _id()
    db = get_db()
    await _run(lambda: db.collection("pois").document(doc_id).set(_flatten_arrays({
        "id": doc_id, "floor_id": floor_id, "name": name,
        "type": type_, "coord_x": coord_x, "coord_y": coord_y,
        "is_safe_exit": is_safe_exit,
    })))
    return doc_id


async def get_pois_on_floor(floor_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("pois").where("floor_id", "==", floor_id).stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def get_exits_on_floor(floor_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("pois")
        .where("floor_id", "==", floor_id)
        .where("is_safe_exit", "==", True)
        .stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def get_poi(poi_id: str) -> dict | None:
    db = get_db()
    doc = await _run(lambda: db.collection("pois").document(poi_id).get())
    return _unflatten_arrays(doc.to_dict()) if doc.exists else None


async def get_poi_chain(poi_id: str) -> dict | None:
    """
    Returns a merged dict of poi + floor + block info.
    Used by the enricher to resolve full physical location in one call.
    """
    poi = await get_poi(poi_id)
    if not poi:
        return None
    floor = await get_floor(poi["floor_id"])
    if not floor:
        return None
    block = await get_block(floor["block_id"])
    if not block:
        return None
    return {**poi, "floor_level": floor["level"], "block_id": block["id"],
            "block_code": block["block_code"], "floor_id": floor["id"],
            "hotel_id": block.get("hotel_id", ""),
            "grid_width": floor["grid_width"], "grid_height": floor["grid_height"]}


# ──────────────────────────────────────────────────────────────────
# CAMERAS
# ──────────────────────────────────────────────────────────────────

async def save_camera(block_id: str, floor_id: str, coord_x: int,
                      coord_y: int, stream_url: str,
                      coverage_zones: list[dict]) -> str:
    doc_id = _id()
    db = get_db()
    cam_data = {
        "id": doc_id, "block_id": block_id, "floor_id": floor_id,
        "coord_x": coord_x, "coord_y": coord_y,
        "stream_url": stream_url, "active": True,
    }
    await _run(lambda: db.collection("cameras").document(doc_id).set(_flatten_arrays(cam_data)))

    for z in coverage_zones:
        zone_id = _id()
        await _run(lambda z=z, zid=zone_id: (
            db.collection("cameras").document(doc_id)
            .collection("coverage_zones").document(zid)
            .set(_flatten_arrays({"id": zid, "camera_id": doc_id, **z}))
        ))
    return doc_id


async def get_cameras_on_floor(floor_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("cameras")
        .where("floor_id", "==", floor_id)
        .where("active", "==", True)
        .stream()
    ))
    result = []
    for doc in docs:
        cam = _unflatten_arrays(doc.to_dict())
        zone_docs = await _run(lambda d=doc: list(
            d.reference.collection("coverage_zones").stream()
        ))
        cam["coverage_zones"] = [_unflatten_arrays(z.to_dict()) for z in zone_docs]
        result.append(cam)
    return result


# ──────────────────────────────────────────────────────────────────
# STAFF
# ──────────────────────────────────────────────────────────────────

async def get_on_duty_staff(hotel_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("staff")
        .where("hotel_id", "==", hotel_id)
        .where("on_duty", "==", True)
        .stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def update_staff_location(staff_id: str, floor_id: str, block_id: str) -> None:
    db = get_db()
    await _run(lambda: db.collection("staff").document(staff_id).update({
        "current_floor_id": floor_id,
        "current_block_id": block_id,
    }))


async def get_staff_on_floor(floor_id: str, block_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("staff")
        .where("current_floor_id", "==", floor_id)
        .where("current_block_id", "==", block_id)
        .where("on_duty", "==", True)
        .stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


# ──────────────────────────────────────────────────────────────────
# ROOM OCCUPANTS (NEW)
# ──────────────────────────────────────────────────────────────────

async def save_room_occupant(
    room_id: str,
    hotel_id: str, floor_id: str, block_id: str,
    room_name: str, room_number: str, block_code: str,
    floor_level: int, coord_x: int, coord_y: int,
    name: str, phone: str,
    fcm_token: str | None = None,
    language: str = "en",
) -> None:
    """
    Creates or updates the room_occupants document for room_id.
    If the room doc already exists, appends to the occupants array.
    """
    db = get_db()
    ref = db.collection("room_occupants").document(room_id)

    def _upsert():
        doc = ref.get()
        occupant = {
            "name": name, "phone": phone,
            "fcm_token": fcm_token, "language": language,
            "checked_in_at": _now(),
        }
        if doc.exists:
            data = doc.to_dict()
            occupants = data.get("occupants", [])
            # Replace if same phone, else append
            occupants = [o for o in occupants if o["phone"] != phone]
            occupants.append(occupant)
            ref.update({"occupants": occupants})
        else:
            ref.set(_flatten_arrays({
                "room_id": room_id, "hotel_id": hotel_id,
                "floor_id": floor_id, "block_id": block_id,
                "room_name": room_name, "room_number": room_number,
                "block_code": block_code, "floor_level": floor_level,
                "coord_x": coord_x, "coord_y": coord_y,
                "occupants": [occupant],
            }))

    await _run(_upsert)


async def remove_room_occupant(room_id: str, phone: str) -> None:
    """Check out a single guest from a room by phone number."""
    db = get_db()
    ref = db.collection("room_occupants").document(room_id)

    def _remove():
        doc = ref.get()
        if not doc.exists:
            return
        data = doc.to_dict()
        updated = [o for o in data.get("occupants", []) if o["phone"] != phone]
        ref.update({"occupants": updated})

    await _run(_remove)


async def update_fcm_token(room_id: str, phone: str, fcm_token: str) -> None:
    """Guest PWA registers its FCM device token after granting notification permission."""
    db = get_db()
    ref = db.collection("room_occupants").document(room_id)

    def _update():
        doc = ref.get()
        if not doc.exists:
            return
        data = doc.to_dict()
        for o in data.get("occupants", []):
            if o["phone"] == phone:
                o["fcm_token"] = fcm_token
        ref.update({"occupants": data["occupants"]})

    await _run(_update)


async def get_room_occupants_on_floor(floor_id: str) -> list[dict]:
    """Returns all occupied rooms on a floor — used by FCM notifier at incident time."""
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("room_occupants").where("floor_id", "==", floor_id).stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def get_room_occupants_on_adj_floors(block_id: str, levels: list[int]) -> list[dict]:
    """Rooms on adjacent floors in same block — zone 2 notifications."""
    db = get_db()
    results = []
    floors = await _run(lambda: list(
        db.collection("floors")
        .where("block_id", "==", block_id)
        .stream()
    ))
    floor_ids = [f.to_dict()["id"] for f in floors if f.to_dict().get("level") in levels]
    for fid in floor_ids:
        docs = await _run(lambda fid=fid: list(
            db.collection("room_occupants").where("floor_id", "==", fid).stream()
        ))
    return results


# ──────────────────────────────────────────────────────────────────
# CHAT / SESSIONS
# ──────────────────────────────────────────────────────────────────

async def save_chat_session(
    session_id: str, hotel_id: str,
    poi_id: str | None = None, sender_type: str = "guest",
) -> None:
    db = get_db()
    await _run(lambda: db.collection("chat_sessions").document(session_id).set(_flatten_arrays({
        "id": session_id, "hotel_id": hotel_id,
        "poi_id": poi_id, "sender_type": sender_type,
        "started_at": _now(), "last_active": _now(),
    })))


async def get_chat_session(session_id: str) -> dict | None:
    db = get_db()
    doc = await _run(lambda: db.collection("chat_sessions").document(session_id).get())
    return _unflatten_arrays(doc.to_dict()) if doc.exists else None


async def save_chat_message(msg: dict) -> None:
    db = get_db()
    msg_id = msg.get("id", _id())
    await _run(lambda: db.collection("chat_messages").document(msg_id).set(_flatten_arrays(msg)))


# ──────────────────────────────────────────────────────────────────
# INCIDENTS
# ──────────────────────────────────────────────────────────────────

async def save_incident(incident: dict) -> str:
    db = get_db()
    doc_id = incident.get("id", _id())
    incident["id"] = doc_id
    await _run(lambda: db.collection("incidents").document(doc_id).set(_flatten_arrays(incident)))
    return doc_id


async def get_incident(incident_id: str) -> dict | None:
    db = get_db()
    doc = await _run(lambda: db.collection("incidents").document(incident_id).get())
    return _unflatten_arrays(doc.to_dict()) if doc.exists else None


async def list_active_incidents(hotel_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("incidents")
        .where("hotel_id", "==", hotel_id)
        .where("status", "==", "active")
        .stream()
    ))
    return sorted([_unflatten_arrays(d.to_dict()) for d in docs],
                  key=lambda x: x.get("detected_at", ""), reverse=True)


async def update_incident_status(incident_id: str, status: str,
                                  blocked_nodes: list | None = None) -> None:
    db = get_db()
    updates: dict[str, Any] = {"status": status}
    if status == "resolved":
        updates["resolved_at"] = _now()
        updates["blocked_nodes"] = []
    if blocked_nodes is not None:
        updates["blocked_nodes"] = blocked_nodes
    await _run(lambda: db.collection("incidents").document(incident_id).update(_flatten_arrays(updates)))


async def save_emergency_alert(alert: dict) -> str:
    db = get_db()
    doc_id = alert.get("id", _id())
    alert["id"] = doc_id
    await _run(lambda: db.collection("emergency_alerts").document(doc_id).set(_flatten_arrays(alert)))
    return doc_id


async def get_alerts_for_incident(incident_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("emergency_alerts")
        .where("incident_id", "==", incident_id)
        .stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


# ──────────────────────────────────────────────────────────────────
# DISPATCHES
# ──────────────────────────────────────────────────────────────────

async def save_dispatch(dispatch: dict) -> str:
    db = get_db()
    doc_id = dispatch.get("id", _id())
    dispatch["id"] = doc_id
    await _run(lambda: db.collection("dispatches").document(doc_id).set(_flatten_arrays(dispatch)))
    return doc_id


async def ack_dispatch(dispatch_id: str) -> None:
    db = get_db()
    await _run(lambda: db.collection("dispatches").document(dispatch_id).update({
        "ack_status": "ACCEPTED", "acked_at": _now(),
    }))


async def get_dispatches_for_incident(incident_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("dispatches")
        .where("incident_id", "==", incident_id)
        .stream()
    ))
    return [_unflatten_arrays(d.to_dict()) for d in docs]


async def get_pending_dispatches(hotel_id: str) -> list[dict]:
    db = get_db()
    docs = await _run(lambda: list(
        db.collection("dispatches")
        .where("ack_status", "==", "PENDING")
        .stream()
    ))
    # Filter by hotel via incident lookup
    result = []
    for d in docs:
        data = d.to_dict()
        inc = await get_incident(data["incident_id"])
        if inc and inc.get("hotel_id") == hotel_id and inc.get("status") == "active":
            result.append({**data, "_incident": inc})
    return result


# ──────────────────────────────────────────────────────────────────
# REAL-TIME EVENT CHANNELS (replaces Redis Pub/Sub)
# ──────────────────────────────────────────────────────────────────

async def publish_session_event(session_id: str, event: dict) -> None:
    """
    Publishes an event to sessions/{session_id}/events.
    The WebSocket handler's Firestore on_snapshot listener picks this up
    and forwards it to the connected client.
    """
    db = get_db()
    event_id = _id()
    event["_ts"] = _now()
    await _run(lambda: (
        db.collection("chat_sessions").document(session_id)
        .collection("events").document(event_id).set(_flatten_arrays(event))
    ))


async def publish_staff_event(venue_id: str, event: dict) -> None:
    """Venue-wide broadcast to all connected staff WebSocket sessions."""
    db = get_db()
    event_id = _id()
    event["_ts"] = _now()
    await _run(lambda: (
        db.collection("venues").document(venue_id)
        .collection("staff_events").document(event_id).set(_flatten_arrays(event))
    ))


async def publish_dashboard_event(venue_id: str, event: dict) -> None:
    """Dashboard broadcast for ops panel updates."""
    db = get_db()
    event_id = _id()
    event["_ts"] = _now()
    await _run(lambda: (
        db.collection("venues").document(venue_id)
        .collection("dashboard_events").document(event_id).set(_flatten_arrays(event))
    ))
