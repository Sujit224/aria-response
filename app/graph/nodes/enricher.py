import uuid
from sqlalchemy import select
from app.models.schemas import PipelineState, EnrichedMessage
from app.models.tables import Guest, POI, Floor, Block, ChatSession
from app.db.session import AsyncSessionLocal


async def enricher_node(state: PipelineState) -> PipelineState:
    """
    Resolves physical location from room_id (poi_id):
        pois → floor_id → floors → block_id → blocks

    Also creates or resumes a ChatSession row.
    """
    incoming = state.incoming
    session_id = incoming.session_id

    poi_id        = incoming.room_id
    room_number   = None
    floor_id      = None
    floor_level   = None
    block_id      = None
    block_code    = None
    coord_x       = None
    coord_y       = None

    async with AsyncSessionLocal() as db:

        # ── Location chain: pois → floors → blocks ──────────────
        if poi_id:
            result = await db.execute(
                select(POI, Floor, Block)
                .join(Floor, POI.floor_id == Floor.id)
                .join(Block, Floor.block_id == Block.id)
                .where(POI.id == poi_id)
            )
            row = result.first()
            if row:
                poi, floor, block = row
                room_number = poi.name
                floor_id    = str(floor.id)
                floor_level = floor.level
                block_id    = str(block.id)
                block_code  = block.block_code
                coord_x     = poi.coord_x
                coord_y     = poi.coord_y

        # ── Chat session: resume or create ───────────────────────
        if session_id:
            existing = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            if not existing.scalar_one_or_none():
                session_id = None           # stale id — create fresh

        if not session_id:
            session_id = str(uuid.uuid4())
            poi_ref    = poi_id if poi_id else None
            new_sess   = ChatSession(
                id          = session_id,
                hotel_id    = incoming.venue_id,
                poi_id      = poi_ref,
                sender_type = "guest",
            )
            db.add(new_sess)
            await db.commit()

    state.enriched = EnrichedMessage(
        session_id  = session_id,
        venue_id    = incoming.venue_id,
        raw_text    = incoming.raw_text,
        language    = incoming.language,
        poi_id      = poi_id,
        room_number = room_number,
        floor_id    = floor_id,
        floor_level = floor_level,
        block_id    = block_id,
        block_code  = block_code,
        coord_x     = coord_x,
        coord_y     = coord_y,
    )
    return state