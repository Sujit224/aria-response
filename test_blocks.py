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
    docs = await asyncio.get_event_loop().run_in_executor(None, lambda: list(
        db.collection('blocks').where('hotel_id', '==', venue_id).stream()
    ))
    for d in docs:
        print(f"Block: {d.to_dict().get('name')} - {d.to_dict().get('block_code')} - {d.id}")

asyncio.run(test())
