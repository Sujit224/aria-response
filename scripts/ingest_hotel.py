"""
Usage:
    python scripts/ingest_hotel.py --file scripts/sample_hotel.json

Seeds Firestore with the hotel structure from a JSON floor plan file.
Run once after setting up FIREBASE_CREDENTIALS_PATH in .env.
The script prints the hotel_id — set it as VENUE_ID in .env.
"""
import asyncio
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import app.db.firebase as firebase
from app.db.collections import (
    save_hotel, save_block, save_floor, save_poi, save_camera,
)


async def ingest(filepath: str):
    with open(filepath) as f:
        data = json.load(f)

    firebase.initialize()

    # ── Hotel ────────────────────────────────────────────────
    hotel_id = await save_hotel(
        name    = data["hotel"]["name"],
        address = data["hotel"]["address"],
    )
    print(f"[+] Hotel: {data['hotel']['name']} ({hotel_id})")

    # ── Blocks ───────────────────────────────────────────────
    block_map = {}
    for b in data["blocks"]:
        block_id = await save_block(hotel_id, b["name"], b["block_code"])
        block_map[b["block_code"]] = block_id
        print(f"  [+] Block {b['block_code']}: {b['name']} ({block_id})")

    # ── Floors, POIs, Cameras ────────────────────────────────
    for block_entry in data.get("floors_per_block", []):
        block_id = block_map[block_entry["block_code"]]

        for floor_data in block_entry["floors"]:
            floor_id = await save_floor(
                block_id    = block_id,
                level       = floor_data["level"],
                grid_width  = floor_data["grid_width"],
                grid_height = floor_data["grid_height"],
                static_grid = floor_data["static_grid"],
            )
            print(f"    [+] Floor {floor_data['level']} ({floor_id})")

            for p in floor_data.get("pois", []):
                await save_poi(
                    floor_id     = floor_id,
                    name         = p["name"],
                    type_        = p["type"],
                    coord_x      = p["coord_x"],
                    coord_y      = p["coord_y"],
                    is_safe_exit = p.get("is_safe_exit", False),
                )
            print(f"      [+] {len(floor_data.get('pois', []))} POIs")

            for c in floor_data.get("cameras", []):
                await save_camera(
                    block_id       = block_id,
                    floor_id       = floor_id,
                    coord_x        = c["coord_x"],
                    coord_y        = c["coord_y"],
                    stream_url     = c["stream_url"],
                    coverage_zones = c.get("coverage_zones", []),
                )
            print(f"      [+] {len(floor_data.get('cameras', []))} cameras")

    print(f"\n[OK] Hotel '{data['hotel']['name']}' written to Firestore.")
    print(f"    hotel_id = {hotel_id}")
    print(f"\n    --> Add this to your .env:")
    print(f"       VENUE_ID={hotel_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="scripts/sample_hotel.json")
    args = parser.parse_args()
    asyncio.run(ingest(args.file))