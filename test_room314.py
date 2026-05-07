import asyncio
import os
from dotenv import load_dotenv
import app.db.firebase as firebase
from app.db.collections import get_poi_chain, get_on_duty_staff

load_dotenv()
firebase.initialize()

ROOM_ID = "25b4cbcb-4afa-4da8-8fce-79f9bfcc780c"  # Room 314

async def test():
    venue_id = os.getenv('VENUE_ID')
    chain = await get_poi_chain(ROOM_ID)
    if not chain:
        print("Room not found in Firestore!")
        return

    block_id = chain['block_id']
    floor_id = chain['floor_id']
    print(f"Room: {chain['name']}")
    print(f"  block_id: {block_id}")
    print(f"  floor_id: {floor_id}")
    print(f"  block_code: {chain['block_code']}")
    print(f"  floor_level: {chain['floor_level']}")

    all_staff = await get_on_duty_staff(venue_id)
    block_staff = [s for s in all_staff if s.get("current_block_id") == block_id or s.get("block_id") == block_id]
    available = [s for s in block_staff if s.get("current_floor_id") == floor_id or not s.get("current_floor_id")]

    print(f"\nTotal on-duty staff: {len(all_staff)}")
    print(f"Block staff: {len(block_staff)} => {[s['name'] for s in block_staff]}")
    print(f"Available: {len(available)} => {[s['name'] for s in available]}")

asyncio.run(test())
