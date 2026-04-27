from fastapi import APIRouter, HTTPException
from app.db.collections import (
    save_hotel, list_hotels,
    save_block, list_blocks,
    save_floor, list_floors, get_floor,
    save_poi,
    save_camera,
)
from app.models.schemas import (
    CreateHotelRequest, CreateBlockRequest,
    FloorGridRequest, POIRequest, CreateCameraRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Hotel ──────────────────────────────────────────────────────────

@router.post("/hotel")
async def create_hotel(body: CreateHotelRequest):
    hotel_id = await save_hotel(body.name, body.address)
    return {"hotel_id": hotel_id, "name": body.name}


@router.get("/hotels")
async def get_hotels():
    return await list_hotels()


# ── Blocks ─────────────────────────────────────────────────────────

@router.post("/blocks")
async def create_block(body: CreateBlockRequest):
    block_id = await save_block(body.hotel_id, body.name, body.block_code)
    return {"block_id": block_id, "block_code": body.block_code}


@router.get("/blocks/{hotel_id}")
async def get_blocks(hotel_id: str):
    return await list_blocks(hotel_id)


# ── Floors ─────────────────────────────────────────────────────────

@router.post("/floors/grid")
async def create_floor_grid(body: FloorGridRequest):
    floor_id = await save_floor(
        body.block_id, body.level,
        body.grid_width, body.grid_height, body.static_grid,
    )
    return {"floor_id": floor_id, "level": body.level, "block_id": body.block_id}


@router.get("/floors/{block_id}")
async def get_floors(block_id: str):
    floors = await list_floors(block_id)
    return [{"id": f["id"], "level": f["level"],
             "grid_width": f["grid_width"], "grid_height": f["grid_height"]}
            for f in floors]


@router.get("/floors/{floor_id}/grid")
async def get_floor_grid(floor_id: str):
    floor = await get_floor(floor_id)
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")
    return floor


# ── POIs ───────────────────────────────────────────────────────────

@router.post("/pois")
async def create_poi(body: POIRequest):
    poi_id = await save_poi(
        body.floor_id, body.name, body.type,
        body.coord_x, body.coord_y, body.is_safe_exit,
    )
    return {"poi_id": poi_id, "name": body.name, "type": body.type}


@router.post("/pois/bulk")
async def create_pois_bulk(pois: list[POIRequest]):
    count = 0
    for p in pois:
        await save_poi(p.floor_id, p.name, p.type,
                       p.coord_x, p.coord_y, p.is_safe_exit)
        count += 1
    return {"created": count}


# ── Cameras ────────────────────────────────────────────────────────

@router.post("/cameras")
async def create_camera(body: CreateCameraRequest):
    zones = [z.dict() for z in body.coverage_zones]
    cam_id = await save_camera(
        body.block_id, body.floor_id,
        body.coord_x, body.coord_y, body.stream_url, zones,
    )
    return {"camera_id": cam_id, "zones_created": len(zones)}


@router.post("/cameras/bulk")
async def create_cameras_bulk(cameras: list[CreateCameraRequest]):
    count = 0
    for body in cameras:
        zones = [z.dict() for z in body.coverage_zones]
        await save_camera(
            body.block_id, body.floor_id,
            body.coord_x, body.coord_y, body.stream_url, zones,
        )
        count += 1
    return {"created": count}