import asyncio
import os
from dotenv import load_dotenv
import app.db.firebase as firebase
from app.db.collections import get_on_duty_staff, get_poi, get_poi_chain

load_dotenv()
firebase.initialize()

async def test():
    venue_id = os.getenv('VENUE_ID')
    all_staff = await get_on_duty_staff(venue_id)
    
    # Get a room
    db = firebase.get_db()
    docs = await asyncio.get_event_loop().run_in_executor(None, lambda: list(
        db.collection('pois').where('type', '==', 'room').limit(1).stream()
    ))
    if not docs:
        print("No rooms found")
        return
    room_id = docs[0].id
    chain = await get_poi_chain(room_id)
    block_id = chain['block_id']
    floor_id = chain['floor_id']
    
    print(f"Room: {chain['name']}, block_id: {block_id}, floor_id: {floor_id}")
    
    block_staff = [
        s for s in all_staff 
        if s.get("current_block_id") == block_id or s.get("block_id") == block_id
    ]
    available_staff = [
        s for s in block_staff 
        if s.get("current_floor_id") == floor_id or not s.get("current_floor_id")
    ]
    
    print(f"Block staff: {len(block_staff)}")
    print(f"Available staff: {len(available_staff)}")
    if available_staff:
        for s in available_staff:
            print(f"  - {s.get('name')} ({s.get('role')})")
    
    # Mock assignments
    for threat in ['medical', 'fire']:
        assigned = []
        if threat == "medical":
            medical_staff = [s for s in available_staff if s.get("role") == "medical"]
            wardens = [s for s in available_staff if s.get("role") == "warden"]
            assigned = medical_staff + wardens
        else:
            security_staff = [s for s in available_staff if s.get("role") == "security"]
            wardens = [s for s in available_staff if s.get("role") == "warden"]
            assigned = security_staff + wardens
        if not assigned:
            assigned = available_staff[:1]
        print(f"Assigned for {threat}: {[s.get('name') for s in assigned]}")

asyncio.run(test())
