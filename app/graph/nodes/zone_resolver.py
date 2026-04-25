import uuid
from sqlalchemy import select, and_
from app.models.schemas import PipelineState, ZoneResolution, Coord
from app.models.tables import POI, Floor, Block, Staff, Incident, EmergencyAlert
from app.db.session import AsyncSessionLocal
from app.services.pathfinding import astar

SEVERITY_INT = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "NONE": 1}


async def zone_resolver_node(state: PipelineState) -> PipelineState:
    """
    1. Loads the floor's static_grid from DB
    2. Queries POIs to find zone 1/2/3 rooms
    3. Finds nearest safe exit POI
    4. Runs A* from guest coord → exit (no blocked nodes yet at first detection)
    5. Finds on-duty staff on this floor+block
    6. Writes Incident + EmergencyAlert rows
    """
    nlp       = state.nlp
    incident_id = str(uuid.uuid4())

    if not nlp.floor_id or not nlp.block_id:
        state.error = "Cannot resolve zone: guest has no room assignment in DB."
        return state

    async with AsyncSessionLocal() as db:

        # ── Load floor grid ──────────────────────────────────────
        floor_res = await db.execute(
            select(Floor).where(Floor.id == nlp.floor_id)
        )
        floor = floor_res.scalar_one_or_none()
        if not floor:
            state.error = f"Floor {nlp.floor_id} not found."
            return state

        # ── Load block ───────────────────────────────────────────
        block_res = await db.execute(
            select(Block).where(Block.id == nlp.block_id)
        )
        block = block_res.scalar_one_or_none()

        # ── Zone 1: same floor, same block, room POIs ────────────
        z1_res = await db.execute(
            select(POI)
            .join(Floor, POI.floor_id == Floor.id)
            .where(
                Floor.id == nlp.floor_id,
                POI.type == "room",
                POI.id != nlp.poi_id,
            )
        )
        zone_1_rooms = [
            f"{block.block_code}-{p.name}" for p in z1_res.scalars().all()
        ]

        # ── Zone 2: same block, adjacent floors ──────────────────
        adjacent_floors_res = await db.execute(
            select(Floor)
            .where(
                Floor.block_id == nlp.block_id,
                Floor.level.in_([floor.level - 1, floor.level + 1]),
            )
        )
        adj_floor_ids = [f.id for f in adjacent_floors_res.scalars().all()]

        z2_rooms = []
        if adj_floor_ids:
            z2_res = await db.execute(
                select(POI).where(
                    POI.floor_id.in_(adj_floor_ids),
                    POI.type == "room",
                )
            )
            z2_rooms = [f"{block.block_code}-{p.name}" for p in z2_res.scalars().all()]

        # ── Zone 3: other blocks, same level ─────────────────────
        other_floors_res = await db.execute(
            select(Floor, Block)
            .join(Block, Floor.block_id == Block.id)
            .where(
                Floor.level == floor.level,
                Floor.block_id != nlp.block_id,
            )
        )
        z3_rooms = []
        for other_floor, other_block in other_floors_res.all():
            z3_res = await db.execute(
                select(POI).where(
                    POI.floor_id == other_floor.id,
                    POI.type == "room",
                )
            )
            z3_rooms += [
                f"{other_block.block_code}-{p.name}" for p in z3_res.scalars().all()
            ]

        # ── Nearest safe exit ────────────────────────────────────
        exits_res = await db.execute(
            select(POI).where(
                POI.floor_id == nlp.floor_id,
                POI.is_safe_exit == True,
            )
        )
        exits = exits_res.scalars().all()
        if not exits:
            state.error = "No safe exits found on this floor."
            return state

        # Pick nearest exit by Manhattan distance from guest coord
        guest_x = nlp.coord_x or 0
        guest_y = nlp.coord_y or 0
        nearest_exit = min(
            exits,
            key=lambda e: abs(e.coord_x - guest_x) + abs(e.coord_y - guest_y)
        )

        # ── Nearest aid kit ──────────────────────────────────────
        aid_res = await db.execute(
            select(POI).where(
                POI.floor_id == nlp.floor_id,
                POI.type == "medical",
            )
        )
        aid_kits = aid_res.scalars().all()
        nearest_aid = (
            min(aid_kits, key=lambda a: abs(a.coord_x - guest_x) + abs(a.coord_y - guest_y)).name
            if aid_kits else "Front desk"
        )

        # ── A* pathfinding ───────────────────────────────────────
        grid   = floor.static_grid   # List[List[int]]
        path   = astar(
            grid   = grid,
            start  = (guest_x, guest_y),
            end    = (nearest_exit.coord_x, nearest_exit.coord_y),
            blocked = [],
        )
        evac_path      = [Coord(x=c[0], y=c[1]) for c in path]
        blocked_nodes  = []   # empty at first detection; filled when fire spreads

        # ── On-duty staff on this floor+block ────────────────────
        staff_res = await db.execute(
            select(Staff).where(
                and_(
                    Staff.current_floor_id == nlp.floor_id,
                    Staff.current_block_id == nlp.block_id,
                    Staff.on_duty == True,
                )
            )
        )
        staff_on_floor = [str(s.id) for s in staff_res.scalars().all()]

        full_location = (
            f"Block {block.block_code}, {nlp.room_number}, Floor {floor.level}"
        )

        # ── Persist Incident ─────────────────────────────────────
        sev_int = SEVERITY_INT.get(nlp.severity, 3)
        incident = Incident(
            id             = incident_id,
            hotel_id       = nlp.venue_id,
            floor_id       = nlp.floor_id,
            camera_id      = None,
            message_id     = nlp.message_id,
            origin_poi_id  = nlp.poi_id,
            type           = nlp.threat_type,
            severity       = sev_int,
            status         = "active",
            source         = "chat",
            full_location  = full_location,
            blocked_nodes  = [],
        )
        db.add(incident)

        # ── Persist EmergencyAlert ───────────────────────────────
        alert = EmergencyAlert(
            incident_id   = incident_id,
            floor_id      = nlp.floor_id,
            blocked_nodes = [],
            radius        = 0.0,
        )
        db.add(alert)
        await db.commit()

    state.zone = ZoneResolution(
        incident_id       = incident_id,
        threat_type       = nlp.threat_type,
        severity          = nlp.severity,
        source            = "chat",
        room_number       = nlp.room_number or "unknown",
        block_code        = block.block_code,
        floor_level       = floor.level,
        full_location     = full_location,
        zone_1_rooms      = zone_1_rooms,
        zone_2_rooms      = z2_rooms,
        zone_3_rooms      = z3_rooms,
        nearest_exit_name = nearest_exit.name,
        nearest_exit_coord = Coord(x=nearest_exit.coord_x, y=nearest_exit.coord_y),
        nearest_aid_kit   = nearest_aid,
        evacuation_path   = evac_path,
        blocked_nodes     = blocked_nodes,
        staff_on_floor    = staff_on_floor,
        session_id        = nlp.session_id,
        venue_id          = nlp.venue_id,
        message_id        = nlp.message_id,
    )
    return state
