import asyncio
import os
from dotenv import load_dotenv
import app.db.firebase as firebase
from app.db.collections import get_on_duty_staff

load_dotenv()
firebase.initialize()

async def test():
    venue_id = os.getenv('VENUE_ID')
    all_staff = await get_on_duty_staff(venue_id)
    print(f'Total staff for {venue_id}: {len(all_staff)}')
    
    for s in all_staff:
        name = s.get('name')
        role = s.get('role')
        b_id = s.get('block_id')
        cb_id = s.get('current_block_id')
        cf_id = s.get('current_floor_id')
        print(f'{name}: role={role}, block={b_id}, curr_block={cb_id}, curr_floor={cf_id}')

asyncio.run(test())
