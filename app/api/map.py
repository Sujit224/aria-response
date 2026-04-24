from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.session import get_db
from app.models.tables import Floor, POI, Camera, CameraCoverageZone, Guest, Block

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/floor/{floor_id}")
async def get_floor_map(floor_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns the static_grid matrix + all POIs for a floor.
    Frontend uses this to:
      - Render the walkable/wall grid in Three.js or SVG
      - Place room labels, exit markers and stairwell icons
      - Set up the A* coordinate space
    """
    floor_res = await db.execute(select(Floor).where(Floor.id == floor_id))
    floor = floor_res.scalar_one_or_none()
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    poi_res = await db.execute(select(POI).where(POI.floor_id == floor_id))
    pois = poi_res.scalars().all()

    return {
        "floor_id":    floor.id,
        "level":       floor.level,
        "grid_width":  floor.grid_width,
        "grid_height": floor.grid_height,
        "static_grid": floor.static_grid,
        "pois": [
            {
                "id":          p.id,
                "name":        p.name,
                "type":        p.type,
                "coord_x":     p.coord_x,
                "coord_y":     p.coord_y,
                "is_safe_exit": p.is_safe_exit,
            }
            for p in pois
        ],
    }


@router.get("/cameras/{floor_id}")
async def get_floor_cameras(floor_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns camera positions + their coverage zone rectangles for a floor.
    Staff dashboard uses this to:
      - Place camera icons on the 3D map
      - Draw FOV cones over coverage zones
      - Pulse orange when a detection occurs in that zone
    """
    cam_res = await db.execute(
        select(Camera).where(
            and_(Camera.floor_id == floor_id, Camera.active == True)
        )
    )
    cameras = cam_res.scalars().all()

    result = []
    for cam in cameras:
        zone_res = await db.execute(
            select(CameraCoverageZone).where(CameraCoverageZone.camera_id == cam.id)
        )
        zones = zone_res.scalars().all()
        result.append({
            "camera_id":  cam.id,
            "coord_x":    cam.coord_x,
            "coord_y":    cam.coord_y,
            "stream_url": cam.stream_url,
            "coverage_zones": [
                {
                    "zone_name": z.zone_name,
                    "start_x":  z.start_x,
                    "start_y":  z.start_y,
                    "end_x":    z.end_x,
                    "end_y":    z.end_y,
                }
                for z in zones
            ],
        })
    return result


@router.get("/blocks/{hotel_id}")
async def get_hotel_blocks(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns all blocks with their floor list for the 3D navigator.
    Used by Hotel3D.jsx to know how many blocks and floors to render.
    """
    block_res = await db.execute(select(Block).where(Block.hotel_id == hotel_id))
    blocks = block_res.scalars().all()

    result = []
    for block in blocks:
        floor_res = await db.execute(
            select(Floor).where(Floor.block_id == block.id).order_by(Floor.level)
        )
        floors = floor_res.scalars().all()
        result.append({
            "block_id":   block.id,
            "block_code": block.block_code,
            "name":       block.name,
            "floors": [
                {"floor_id": f.id, "level": f.level,
                 "grid_width": f.grid_width, "grid_height": f.grid_height}
                for f in floors
            ],
        })
    return result


@router.get("/guest/location")
async def get_guest_location(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns the guest's current room name and grid coordinates.
    Guest PWA calls this on load to show their position on the floor map.
    """
    guest_res = await db.execute(
        select(Guest).where(Guest.session_id == session_id)
    )
    guest = guest_res.scalar_one_or_none()
    if not guest or not guest.poi_id:
        raise HTTPException(status_code=404, detail="Guest location not found")

    poi_res = await db.execute(select(POI).where(POI.id == guest.poi_id))
    poi = poi_res.scalar_one_or_none()
    if not poi:
        raise HTTPException(status_code=404, detail="Room POI not found")

    floor_res = await db.execute(select(Floor).where(Floor.id == poi.floor_id))
    floor = floor_res.scalar_one_or_none()

    block_res = await db.execute(select(Block).where(Block.id == floor.block_id))
    block = block_res.scalar_one_or_none()

    return {
        "room_name":   poi.name,
        "coord_x":     poi.coord_x,
        "coord_y":     poi.coord_y,
        "floor_level": floor.level,
        "floor_id":    str(floor.id),
        "block_code":  block.block_code,
        "block_id":    str(block.id),
    }