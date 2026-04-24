"""
Usage:
    python scripts/ingest_hotel.py --file scripts/sample_hotel.json

Seeds the database with the hotel structure from a JSON floor plan file.
Run once after first launch to populate the digital twin tables.
"""
import asyncio
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import AsyncSessionLocal, init_db
from app.models.tables import Hotel, Block, Floor, POI, Camera, CameraCoverageZone


async def ingest(filepath: str):
    with open(filepath) as f:
        data = json.load(f)

    await init_db()

    async with AsyncSessionLocal() as db:

        # ── Hotel ────────────────────────────────────────────────
        hotel = Hotel(
            name    = data["hotel"]["name"],
            address = data["hotel"]["address"],
        )
        db.add(hotel)
        await db.flush()
        print(f"[+] Hotel: {hotel.name} ({hotel.id})")

        # ── Blocks ───────────────────────────────────────────────
        block_map = {}   # block_code → Block instance
        for b in data["blocks"]:
            block = Block(
                hotel_id   = hotel.id,
                name       = b["name"],
                block_code = b["block_code"],
            )
            db.add(block)
            await db.flush()
            block_map[b["block_code"]] = block
            print(f"  [+] Block {block.block_code}: {block.name} ({block.id})")

        # ── Floors, POIs, Cameras ────────────────────────────────
        for block_entry in data.get("floors_per_block", []):
            block = block_map[block_entry["block_code"]]

            for floor_data in block_entry["floors"]:
                floor = Floor(
                    block_id    = block.id,
                    level       = floor_data["level"],
                    grid_width  = floor_data["grid_width"],
                    grid_height = floor_data["grid_height"],
                    static_grid = floor_data["static_grid"],
                )
                db.add(floor)
                await db.flush()
                print(f"    [+] Floor {floor.level} (grid {floor.grid_width}x{floor.grid_height}) ({floor.id})")

                # POIs
                for p in floor_data.get("pois", []):
                    poi = POI(
                        floor_id     = floor.id,
                        name         = p["name"],
                        type         = p["type"],
                        coord_x      = p["coord_x"],
                        coord_y      = p["coord_y"],
                        is_safe_exit = p.get("is_safe_exit", False),
                    )
                    db.add(poi)
                print(f"      [+] {len(floor_data.get('pois', []))} POIs")

                # Cameras + coverage zones
                for c in floor_data.get("cameras", []):
                    cam = Camera(
                        block_id   = block.id,
                        floor_id   = floor.id,
                        coord_x    = c["coord_x"],
                        coord_y    = c["coord_y"],
                        stream_url = c["stream_url"],
                        active     = True,
                    )
                    db.add(cam)
                    await db.flush()

                    for z in c.get("coverage_zones", []):
                        zone = CameraCoverageZone(
                            camera_id = cam.id,
                            zone_name = z["zone_name"],
                            start_x   = z["start_x"],
                            start_y   = z["start_y"],
                            end_x     = z["end_x"],
                            end_y     = z["end_y"],
                        )
                        db.add(zone)

                print(f"      [+] {len(floor_data.get('cameras', []))} cameras")

        await db.commit()
        print(f"\n[✓] Hotel '{hotel.name}' ingested successfully.")
        print(f"    hotel_id = {hotel.id}")
        print(f"    Set VENUE_ID={hotel.id} in your .env")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="scripts/sample_hotel.json")
    args = parser.parse_args()
    asyncio.run(ingest(args.file))