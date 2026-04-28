"""
Usage:
    python scripts/ingest_hotel.py --file scripts/hotel_seed.json

Seeds Firestore with the hotel structure from a flattened JSON seed file.
Run once after setting up FIREBASE_CREDENTIALS_PATH in .env.
The script prints the hotel_id — set it as VENUE_ID in .env.
"""
import asyncio
import argparse
import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import app.db.firebase as firebase
from app.db.collections import _flatten_arrays, _now

async def ingest_item(item):
    db = firebase.get_db()
    collection = item["collection"]
    doc_id = item["doc_id"]
    data = item["data"]
    
    # Add timestamps if not present
    if "created_at" not in data:
        data["created_at"] = _now()
    data["updated_at"] = _now()
    
    print(f"  [+] Saving {collection}/{doc_id}...")
    
    # Run sync Firestore call in executor
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: db.collection(collection).document(doc_id).set(_flatten_arrays(data)))

async def ingest(filepath: str):
    firebase.initialize()
    
    if not os.path.exists(filepath):
        print(f"[!] Seed file not found: {filepath}")
        return

    with open(filepath, "r") as f:
        seed_data = json.load(f)

    print(f"[+] Ingesting Hotel: {seed_data['hotel']['data']['name']}")
    await ingest_item(seed_data["hotel"])

    print(f"[+] Ingesting {len(seed_data['blocks'])} Blocks...")
    for block in seed_data["blocks"]:
        await ingest_item(block)

    print(f"[+] Ingesting {len(seed_data['floors'])} Floors...")
    for floor in seed_data["floors"]:
        await ingest_item(floor)

    print(f"[+] Ingesting {len(seed_data['pois'])} POIs...")
    # Ingest POIs in chunks to avoid overwhelming the connection
    chunk_size = 50
    for i in range(0, len(seed_data["pois"]), chunk_size):
        chunk = seed_data["pois"][i:i + chunk_size]
        tasks = [ingest_item(poi) for poi in chunk]
        await asyncio.gather(*tasks)

    hotel_id = seed_data['hotel']['doc_id']
    print(f"\n[OK] Ingestion complete.")
    print(f"Hotel ID: {hotel_id}")
    print(f"\n    --> Add this to your .env:")
    print(f"       VENUE_ID={hotel_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="scripts/hotel_seed.json")
    args = parser.parse_args()
    asyncio.run(ingest(args.file))