from fastapi import APIRouter, HTTPException, Query
from app.db.firebase import get_db
from app.db.collections import (
    get_floor, get_pois_on_floor,
    get_cameras_on_floor, list_blocks, list_floors,
)

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/pois")
async def list_all_pois(
    type: str = Query(None),
    limit: int = Query(200),
    hotel_id: str = Query(None),
):
    """
    Returns POIs for the given hotel, optionally filtered by type (e.g. 'room').
    Queries Firestore via the block/floor chain for this hotel.
    """
    import os
    db = get_db()
    venue_id = hotel_id or os.getenv("VENUE_ID", "")
    if not venue_id:
        return []

    try:
        # Get all blocks for this hotel
        loop = __import__("asyncio").get_event_loop()
        blocks = await loop.run_in_executor(None, lambda: list(
            db.collection("blocks").where("hotel_id", "==", venue_id).stream()
        ))
        block_ids = [b.id for b in blocks]
        if not block_ids:
            return []

        # Get all floor IDs for those blocks
        floor_ids = []
        for bid in block_ids:
            floors = await loop.run_in_executor(None, lambda bid=bid: list(
                db.collection("floors").where("block_id", "==", bid).stream()
            ))
            floor_ids.extend([f.id for f in floors])

        if not floor_ids:
            return []

        # Get all POIs for those floors (Firestore 'in' max 10 at a time)
        all_pois = []
        chunks = [floor_ids[i:i+10] for i in range(0, len(floor_ids), 10)]
        for chunk in chunks:
            poi_docs = await loop.run_in_executor(None, lambda c=chunk: list(
                db.collection("pois").where("floor_id", "in", c).stream()
            ))
            all_pois.extend([d.to_dict() for d in poi_docs])

        if type:
            all_pois = [p for p in all_pois if p.get("type") == type]

        return all_pois[:limit]
    except Exception as e:
        print(f"[ARIA-MAP] Error fetching POIs from Firestore: {e}")
        return []



@router.get("/pois/{poi_id}")
async def get_poi_by_id(poi_id: str):
    """Returns a single POI by its ID. Used by the Guest PWA to resolve room names."""
    from app.db.collections import get_poi
    poi = await get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi



@router.get("/floor/{floor_id}")
async def get_floor_map(floor_id: str):
    """
    Returns the static_grid + all POIs for a floor.
    Frontend uses this to render the walkable grid and place POI labels.
    """
    floor = await get_floor(floor_id)
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    pois = await get_pois_on_floor(floor_id)
    return {
        "floor_id":    floor["id"],
        "level":       floor["level"],
        "grid_width":  floor["grid_width"],
        "grid_height": floor["grid_height"],
        "static_grid": floor["static_grid"],
        "pois":        pois,
    }


@router.get("/cameras/{floor_id}")
async def get_floor_cameras(floor_id: str):
    """Returns all active cameras + coverage zones for a floor."""
    return await get_cameras_on_floor(floor_id)


@router.get("/blocks/{hotel_id}")
async def get_hotel_blocks(hotel_id: str):
    """
    Returns all blocks with their floors for the 3D navigator.
    Used by Hotel3D.jsx to know how many blocks and floors to render.
    """
    blocks = await list_blocks(hotel_id)
    result = []
    for block in blocks:
        floors = await list_floors(block["id"])
        result.append({
            "block_id":   block["id"],
            "block_code": block["block_code"],
            "name":       block.get("name"),
            "floors": [
                {"floor_id": f["id"], "level": f["level"],
                 "grid_width": f["grid_width"], "grid_height": f["grid_height"]}
                for f in floors
            ],
        })
    return result