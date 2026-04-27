import uuid
from app.models.schemas import PipelineState, EnrichedMessage
from app.db.collections import get_poi_chain, save_chat_session, get_chat_session


async def enricher_node(state: PipelineState) -> PipelineState:
    """
    Resolves physical location from room_id (poi_id) using Firestore.
    poi chain: pois → floor → block (single get_poi_chain call)

    Also creates or resumes a ChatSession document in Firestore.
    """
    incoming   = state.incoming
    session_id = incoming.session_id
    poi_id     = incoming.room_id

    room_number = floor_id = block_id = block_code = None
    floor_level = coord_x = coord_y = wing = None

    # ── Location chain ───────────────────────────────────────────
    if poi_id:
        chain = await get_poi_chain(poi_id)
        if chain:
            room_number = chain.get("name")
            floor_id    = chain.get("floor_id")
            floor_level = chain.get("floor_level")
            block_id    = chain.get("block_id")
            block_code  = chain.get("block_code")
            coord_x     = chain.get("coord_x")
            coord_y     = chain.get("coord_y")

    # ── Chat session: resume or create ───────────────────────────
    # Always use the original session_id from the client.
    # If no Firestore doc exists yet (first ever message), create it —
    # but NEVER replace session_id with a new UUID, otherwise the CHAT_ACK
    # will be published to a different channel than the WebSocket is listening on.
    if not session_id:
        session_id = str(uuid.uuid4())

    existing = await get_chat_session(session_id)
    if not existing:
        await save_chat_session(
            session_id  = session_id,
            hotel_id    = incoming.venue_id,
            poi_id      = poi_id,
            sender_type = "guest",
        )

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