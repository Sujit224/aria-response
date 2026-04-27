"""
scripts/seed_occupants.py
─────────────────────────
Seeds Firestore room_occupants collection with realistic guest data.
Run AFTER ingest_hotel.py so the POI/floor/block IDs exist.

Usage:
    python scripts/seed_occupants.py

After running, it prints 3 test room URLs you can open directly in
the Guest PWA to simulate a logged-in guest.
"""
import asyncio
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import app.db.firebase as firebase
from app.db.firebase import get_db
from app.db.collections import save_room_occupant, get_poi_chain

# ── Realistic guest names ──────────────────────────────────────────
GUEST_NAMES = [
    "Arjun Mehta", "Priya Sharma", "Ravi Kumar", "Sneha Patel",
    "Vikram Nair", "Ananya Iyer", "Karan Malhotra", "Divya Reddy",
    "Rohit Gupta", "Pooja Joshi", "Amit Verma", "Neha Kapoor",
    "Sanjay Pillai", "Kavitha Rao", "Rahul Bose", "Meera Desai",
    "Aditya Singh", "Sunita Tiwari", "Deepak Khanna", "Anjali Mishra",
    "Vinod Saxena", "Lakshmi Venkat", "Manish Chadha", "Rekha Bhatt",
    "Suresh Nambiar", "Geeta Murthy", "Arun Srivastava", "Swati Jain",
    "Nitesh Pandey", "Shalini Dube", "Pratap Yadav", "Usha Krishnan",
    "Ratan Oberoi", "Tara Shetty", "Gaurav Agarwal", "Nandita Roy",
    "Mohan Lal", "Preeti Bansal", "Ajay Bhatt", "Sushma Reddy",
]

def rand_phone():
    """Generate a random Indian mobile number (+91 6/7/8/9XXXXXXXXX)"""
    prefix = random.choice([6, 7, 8, 9])
    number = random.randint(100_000_000, 999_999_999)
    return f"+91{prefix}{number}"

def rand_lang():
    return random.choice(["en", "en", "en", "hi", "ta", "te", "ml"])

async def seed():
    firebase.initialize()
    db = get_db()
    loop = asyncio.get_event_loop()

    # Fetch all room-type POIs
    print("[SEED] Fetching all room POIs from Firestore...")
    docs = await loop.run_in_executor(None, lambda: list(
        db.collection("pois").where("type", "==", "room").stream()
    ))
    room_pois = [d.to_dict() for d in docs]
    print(f"[SEED] Found {len(room_pois)} rooms to seed.")

    # Pick a consistent random ordering of names
    random.shuffle(GUEST_NAMES)
    name_pool = GUEST_NAMES * 10   # repeat pool to cover all rooms

    seeded_rooms = []
    for i, poi in enumerate(room_pois):
        poi_id = poi["id"]
        chain  = await get_poi_chain(poi_id)
        if not chain:
            print(f"  [!] Could not resolve chain for POI {poi_id}, skipping.")
            continue

        # 1-2 guests per room
        guest_count = random.randint(1, 2)
        for g in range(guest_count):
            guest_name  = name_pool[(i * 2 + g) % len(name_pool)]
            guest_phone = rand_phone()
            await save_room_occupant(
                room_id     = poi_id,
                hotel_id    = chain.get("hotel_id", ""),   
                floor_id    = chain["floor_id"],
                block_id    = chain["block_id"],
                room_name   = chain["name"],
                room_number = chain["name"].replace("Room ", "").replace("Suite ", "").replace("Penthouse ", ""),
                block_code  = chain["block_code"],
                floor_level = chain["floor_level"],
                coord_x     = chain["coord_x"],
                coord_y     = chain["coord_y"],
                name        = guest_name,
                phone       = guest_phone,
                language    = rand_lang(),
            )
            print(f"  [+] {chain['name']} (Floor {chain['floor_level']}, Block {chain['block_code']})"
                  f" <- {guest_name} {guest_phone}")
        
        seeded_rooms.append({
            "room_id":   poi_id,
            "room_name": chain["name"],
            "floor":     chain["floor_level"],
            "block":     chain["block_code"],
        })

    # ── Print 3 test URLs for the Guest PWA ───────────────────────
    venue_id = os.getenv("VENUE_ID", "YOUR_VENUE_ID")
    test_rooms = random.sample(seeded_rooms, min(3, len(seeded_rooms)))

    print(f"\n{'='*60}")
    print(f"[DONE] Seeded {len(seeded_rooms)} rooms with guests!")
    print(f"{'='*60}")
    print(f"\n  Open these URLs in your browser to test as a guest:\n")
    for r in test_rooms:
        url = f"http://localhost:3000?venue={venue_id}&room={r['room_id']}"
        print(f"  Block {r['block']} / Floor {r['floor']} / {r['room_name']}")
        print(f"  --> {url}\n")

    # Also write the first room as the default test room for easy access
    default = test_rooms[0]
    default_url = f"http://localhost:3000?venue={venue_id}&room={default['room_id']}"
    print(f"  DEFAULT TEST ROOM (copy-paste this):")
    print(f"  {default_url}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(seed())
