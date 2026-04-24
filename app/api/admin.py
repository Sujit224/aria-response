from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.tables import Hotel, Block, Floor, POI, Camera, CameraCoverageZone
from app.models.schemas import (
    CreateHotelRequest, CreateBlockRequest,
    FloorGridRequest, POIRequest,
    CreateCameraRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Hotel ─────────────────────────────────────────────────────────

@router.post("/hotel")
async def create_hotel(body: CreateHotelRequest, db: AsyncSession = Depends(get_db)):
    hotel = Hotel(name=body.name, address=body.address)
    db.add(hotel)
    await db.commit()
    await db.refresh(hotel)
    return {"hotel_id": hotel.id, "name": hotel.name}


@router.get("/hotels")
async def list_hotels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Hotel))
    return [{"id": h.id, "name": h.name, "address": h.address} for h in result.scalars()]


# ── Blocks ────────────────────────────────────────────────────────

@router.post("/blocks")
async def create_block(body: CreateBlockRequest, db: AsyncSession = Depends(get_db)):
    block = Block(hotel_id=body.hotel_id, name=body.name, block_code=body.block_code)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return {"block_id": block.id, "block_code": block.block_code}


@router.get("/blocks/{hotel_id}")
async def list_blocks(hotel_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.hotel_id == hotel_id))
    return [{"id": b.id, "name": b.name, "block_code": b.block_code} for b in result.scalars()]


# ── Floors + static_grid ──────────────────────────────────────────

@router.post("/floors/grid")
async def create_floor_grid(body: FloorGridRequest, db: AsyncSession = Depends(get_db)):
    """
    Upload the 2D walkability matrix for one floor of one block.
    static_grid format: [[0,1,0,...], ...]  where 0=walkable, 1=wall.
    This is the grid A* pathfinding runs on at incident time.
    """
    floor = Floor(
        block_id    = body.block_id,
        level       = body.level,
        grid_width  = body.grid_width,
        grid_height = body.grid_height,
        static_grid = body.static_grid,
    )
    db.add(floor)
    await db.commit()
    await db.refresh(floor)
    return {"floor_id": floor.id, "level": floor.level, "block_id": floor.block_id}


@router.get("/floors/{block_id}")
async def list_floors(block_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Floor).where(Floor.block_id == block_id))
    floors = result.scalars().all()
    return [
        {
            "id": f.id, "level": f.level,
            "grid_width": f.grid_width, "grid_height": f.grid_height,
        }
        for f in floors
    ]


@router.get("/floors/{floor_id}/grid")
async def get_floor_grid(floor_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the full static_grid matrix for a floor — used by frontend renderer."""
    result = await db.execute(select(Floor).where(Floor.id == floor_id))
    floor = result.scalar_one_or_none()
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")
    return {
        "floor_id":    floor.id,
        "level":       floor.level,
        "grid_width":  floor.grid_width,
        "grid_height": floor.grid_height,
        "static_grid": floor.static_grid,
    }


# ── POIs ──────────────────────────────────────────────────────────

@router.post("/pois")
async def create_poi(body: POIRequest, db: AsyncSession = Depends(get_db)):
    poi = POI(
        floor_id     = body.floor_id,
        name         = body.name,
        type         = body.type,
        coord_x      = body.coord_x,
        coord_y      = body.coord_y,
        is_safe_exit = body.is_safe_exit,
    )
    db.add(poi)
    await db.commit()
    await db.refresh(poi)
    return {"poi_id": poi.id, "name": poi.name, "type": poi.type}


@router.post("/pois/bulk")
async def create_pois_bulk(pois: list[POIRequest], db: AsyncSession = Depends(get_db)):
    """Bulk-create all rooms, exits and stairwells for a floor in one call."""
    created = []
    for p in pois:
        poi = POI(
            floor_id     = p.floor_id,
            name         = p.name,
            type         = p.type,
            coord_x      = p.coord_x,
            coord_y      = p.coord_y,
            is_safe_exit = p.is_safe_exit,
        )
        db.add(poi)
        created.append(poi)
    await db.commit()
    return {"created": len(created)}


@router.get("/pois/{floor_id}")
async def list_pois(floor_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(POI).where(POI.floor_id == floor_id))
    return [
        {
            "id": p.id, "name": p.name, "type": p.type,
            "coord_x": p.coord_x, "coord_y": p.coord_y,
            "is_safe_exit": p.is_safe_exit,
        }
        for p in result.scalars()
    ]


# ── Cameras ───────────────────────────────────────────────────────

@router.post("/cameras")
async def create_camera(body: CreateCameraRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers a camera with its floor position and coverage zones.
    coverage_zones define the grid rectangles this camera can see —
    used by the vision pipeline to map detections to POIs.
    """
    cam = Camera(
        block_id   = body.block_id,
        floor_id   = body.floor_id,
        coord_x    = body.coord_x,
        coord_y    = body.coord_y,
        stream_url = body.stream_url,
        active     = True,
    )
    db.add(cam)
    await db.flush()   # get cam.id before adding zones

    for z in body.coverage_zones:
        zone = CameraCoverageZone(
            camera_id = cam.id,
            zone_name = z.zone_name,
            start_x   = z.start_x,
            start_y   = z.start_y,
            end_x     = z.end_x,
            end_y     = z.end_y,
        )
        db.add(zone)

    await db.commit()
    await db.refresh(cam)
    return {"camera_id": cam.id, "zones_created": len(body.coverage_zones)}


@router.post("/cameras/bulk")
async def create_cameras_bulk(cameras: list[CreateCameraRequest], db: AsyncSession = Depends(get_db)):
    created = []
    for body in cameras:
        cam = Camera(
            block_id=body.block_id, floor_id=body.floor_id,
            coord_x=body.coord_x, coord_y=body.coord_y,
            stream_url=body.stream_url, active=True,
        )
        db.add(cam)
        await db.flush()
        for z in body.coverage_zones:
            db.add(CameraCoverageZone(
                camera_id=cam.id, zone_name=z.zone_name,
                start_x=z.start_x, start_y=z.start_y,
                end_x=z.end_x, end_y=z.end_y,
            ))
        created.append(cam.id)
    await db.commit()
    return {"created": len(created)}