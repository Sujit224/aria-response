import asyncio
import os
from dotenv import load_dotenv
import app.db.firebase as firebase
from app.db.firebase import get_db

load_dotenv()
firebase.initialize()

async def test():
    venue_id = os.getenv('VENUE_ID')
    db = get_db()
    blocks = await asyncio.get_event_loop().run_in_executor(None, lambda: list(
        db.collection('blocks').where('hotel_id', '==', venue_id).stream()
    ))
    block_ids = [b.id for b in blocks]
    
    floors = await asyncio.get_event_loop().run_in_executor(None, lambda: list(
        db.collection('floors').where('block_id', 'in', block_ids).stream()
    ))
    floor_ids = [f.id for f in floors]
    
    pois = await asyncio.get_event_loop().run_in_executor(None, lambda: list(
        db.collection('pois').where('floor_id', 'in', floor_ids).stream()
    ))
    print(f"POIs in current venue's blocks: {len(pois)}")

    room_pois = await asyncio.get_event_loop().run_in_executor(None, lambda: list(
        db.collection('pois').where('type', '==', 'room').limit(10).stream()
    ))
    for r in room_pois:
        print(f"Global Room: {r.to_dict().get('name')} - {r.to_dict().get('floor_id')}")

asyncio.run(test())
