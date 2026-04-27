import uuid
from app.models.schemas import PipelineState, ZoneResolution, Coord
from app.db.collections import (
    get_floor, get_block,
    get_pois_on_floor, get_exits_on_floor,
    get_staff_on_floor, get_on_duty_staff,
    save_incident, save_emergency_alert,
    list_floors,
)
from app.services.pathfinding import astar
from app.services.fcm_notifier import send_zone_evacuation_notifications

SEVERITY_INT = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "NONE": 1}


async def zone_resolver_node(state: PipelineState) -> PipelineState:
    """
    1. Loads floor + block from Firestore
    2. Queries POIs for zone 1/2/3 rooms
    3. Finds nearest safe exit, runs A*
    4. Persists Incident + EmergencyAlert to Firestore
    5. Fires FCM push notifications to all registered room occupants
    """
    nlp         = state.nlp
    incident_id = str(uuid.uuid4())

    if not nlp.floor_id or not nlp.block_id:
        state.error = "Cannot resolve zone: guest has no room assignment in DB."
        return state

    # ── Load floor + block ───────────────────────────────────────
    floor = await get_floor(nlp.floor_id)
    if not floor:
        state.error = f"Floor {nlp.floor_id} not found."
        return state

    block = await get_block(nlp.block_id)

    # ── All POIs on this floor ───────────────────────────────────
    all_pois = await get_pois_on_floor(nlp.floor_id)

    # Zone 1: same floor rooms (excluding guest's own room)
    zone_1_rooms = [
        f"{block['block_code']}-{p['name']}"
        for p in all_pois
        if p["type"] == "room" and p["id"] != nlp.poi_id
    ]

    # Zone 2: adjacent floors in same block
    all_floors = await list_floors(nlp.block_id)
    adj_floor_ids = [
        f["id"] for f in all_floors
        if f["level"] in (floor["level"] - 1, floor["level"] + 1)
    ]
    z2_rooms = []
    for fid in adj_floor_ids:
        pois_adj = await get_pois_on_floor(fid)
        z2_rooms += [
            f"{block['block_code']}-{p['name']}"
            for p in pois_adj if p["type"] == "room"
        ]

    # Zone 3: other blocks at same level (simplified — list count only)
    zone_3_rooms = []  # leave for future multi-block support

    # ── Nearest safe exit ────────────────────────────────────────
    exits = await get_exits_on_floor(nlp.floor_id)
    if not exits:
        state.error = "No safe exits found on this floor."
        return state

    guest_x = nlp.coord_x or 0
    guest_y = nlp.coord_y or 0

    nearest_exit = min(
        exits,
        key=lambda e: abs(e["coord_x"] - guest_x) + abs(e["coord_y"] - guest_y)
    )

    # ── Nearest aid kit ──────────────────────────────────────────
    aid_kits = [p for p in all_pois if p["type"] == "medical"]
    nearest_aid_kit = (
        min(aid_kits, key=lambda a: abs(a["coord_x"] - guest_x) + abs(a["coord_y"] - guest_y))
        if aid_kits else None
    )
    nearest_aid_name = nearest_aid_kit["name"] if nearest_aid_kit else "Front desk"

    # ── A* pathfinding ───────────────────────────────────────────
    # If minor medical, route to aid kit. Otherwise route to exit.
    target_poi = nearest_exit
    if nlp.threat_type == "medical" and nlp.severity not in ("CRITICAL", "HIGH") and nearest_aid_kit:
        target_poi = nearest_aid_kit

    path = astar(
        grid    = floor["static_grid"],
        start   = (guest_x, guest_y),
        end     = (target_poi["coord_x"], target_poi["coord_y"]),
        blocked = [],
    )
    evac_path     = [Coord(x=c[0], y=c[1]) for c in path]
    target_coord  = Coord(x=target_poi["coord_x"], y=target_poi["coord_y"])
    blocked_nodes = []

    # ── On-duty staff for this incident ──────────────────────────
    all_staff = await get_on_duty_staff(nlp.venue_id)
    block_staff = [
        s for s in all_staff 
        if s.get("current_block_id") == nlp.block_id or s.get("block_id") == nlp.block_id
    ]
    # Include staff assigned to this specific floor, or staff covering the whole block (no specific floor)
    available_staff = [
        s for s in block_staff 
        if s.get("current_floor_id") == nlp.floor_id or not s.get("current_floor_id")
    ]
    
    assigned_staff = []
    if nlp.threat_type == "medical":
        medical_staff = [s for s in available_staff if s.get("role") == "medical"]
        if nlp.severity in ("CRITICAL", "HIGH"):
            wardens = [s for s in available_staff if s.get("role") == "warden"]
            assigned_staff = medical_staff + wardens
        else:
            assigned_staff = medical_staff[:1] # Just one medical person for minor injuries
    else:
        security_staff = [s for s in available_staff if s.get("role") == "security"]
        wardens = [s for s in available_staff if s.get("role") == "warden"]
        if nlp.severity in ("CRITICAL", "HIGH"):
            assigned_staff = security_staff + wardens
        else:
            assigned_staff = wardens[:1] if wardens else security_staff[:1]
            
    if not assigned_staff:
        assigned_staff = available_staff[:1]

    staff_ids = [s["id"] for s in assigned_staff]
    assigned_staff_names = [s.get("name", "Emergency Responder") for s in assigned_staff]

    full_location = f"Block {block['block_code']}, {nlp.room_number}, Floor {floor['level']}"

    # ── Persist Incident to Firestore ────────────────────────────
    sev_int = SEVERITY_INT.get(nlp.severity, 3)
    await save_incident({
        "id":            incident_id,
        "hotel_id":      nlp.venue_id,
        "floor_id":      nlp.floor_id,
        "camera_id":     None,
        "message_id":    nlp.message_id,
        "origin_poi_id": nlp.poi_id,
        "type":          nlp.threat_type,
        "severity":      sev_int,
        "status":        "active",
        "source":        "chat",
        "full_location": full_location,
        "blocked_nodes": [],
        "detected_at":   __import__("datetime").datetime.utcnow().isoformat(),
    })

    # ── Persist EmergencyAlert ───────────────────────────────────
    await save_emergency_alert({
        "id":            str(uuid.uuid4()),
        "incident_id":   incident_id,
        "floor_id":      nlp.floor_id,
        "blocked_nodes": [],
        "radius":        0.0,
    })

    # ── Send FCM push notifications to all room occupants ────────
    # Fire-and-forget — do not await, so the pipeline isn't slowed
    import asyncio
    asyncio.create_task(send_zone_evacuation_notifications(
        incident_type = nlp.threat_type,
        severity      = nlp.severity,
        full_location = full_location,
        floor_id      = nlp.floor_id,
        floor_level   = floor["level"],
        block_id      = nlp.block_id,
        block_code    = block["block_code"],
        blocked_nodes = blocked_nodes,
        incident_id   = incident_id,
    ))

    state.zone = ZoneResolution(
        incident_id        = incident_id,
        threat_type        = nlp.threat_type,
        severity           = nlp.severity,
        source             = "chat",
        room_number        = nlp.room_number or "unknown",
        block_code         = block["block_code"],
        floor_level        = floor["level"],
        full_location      = full_location,
        zone_1_rooms       = zone_1_rooms,
        zone_2_rooms       = z2_rooms,
        zone_3_rooms       = zone_3_rooms,
        nearest_exit_name  = nearest_exit["name"],
        nearest_exit_coord = target_coord,
        nearest_aid_kit    = nearest_aid_name,
        evacuation_path    = evac_path,
        blocked_nodes      = blocked_nodes,
        staff_on_floor     = staff_ids,
        assigned_staff_names = assigned_staff_names,
        static_grid        = floor["static_grid"],
        grid_width         = floor["grid_width"],
        grid_height        = floor["grid_height"],
        guest_coord        = Coord(x=guest_x, y=guest_y),
        all_pois           = all_pois,
        session_id         = nlp.session_id,
        venue_id           = nlp.venue_id,
        message_id         = nlp.message_id,
    )
    return state
