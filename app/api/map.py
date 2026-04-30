from fastapi import APIRouter, HTTPException, Query
from app.db.firebase import get_db
from app.db.collections import (
    get_floor, get_pois_on_floor,
    get_cameras_on_floor, list_blocks, list_floors,
)

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/pois")
async def list_all_pois(type: str = Query(None), limit: int = Query(200)):
    """
    Returns all POIs, optionally filtered by type (e.g. 'room').
    MOCKED for hackathon to avoid Firestore quota limits.
    """
    import json
    try:
        with open("scripts/hotel_seed_firebase.json", "r") as f:
            data = json.load(f)
            pois = data.get("pois", [])
            if type:
                pois = [p for p in pois if p.get("type") == type]
            return pois[:limit]
    except Exception as e:
        print(f"Error reading local POIs: {e}")
        return []


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