"""
scripts/seed_staff.py
─────────────────────
Seeds the `staff` Firestore collection with realistic hotel staff data.
Run AFTER ingest_hotel.py.

Usage:
    python scripts/seed_staff.py

Creates:
  - Security personnel per block
  - Floor wardens per floor
  - Medical/first-aid staff
  - Front desk officers
  - A supervisor / duty manager
"""
import asyncio
import sys
import os
import random
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import app.db.firebase as firebase
from app.db.firebase import get_db

HOTEL_ID = os.getenv("VENUE_ID", "")

# ── Staff roster ───────────────────────────────────────────────────
SECURITY = [
    ("Ramesh Tyagi",    "+919823451100", "A"),
    ("Deepa Nair",      "+918745623001", "A"),
    ("Santhosh Kumar",  "+917654320192", "B"),
    ("Fatima Shaikh",   "+916789012345", "B"),
    ("Ajit Yadav",      "+919012345678", "C"),
    ("Prathima Reddy",  "+918901234567", "C"),
]

WARDENS = [
    # (name, phone, block_code, floor_level)
    ("Harish Menon",    "+919988776601", "A", 1),
    ("Nalini Rao",      "+918877665502", "A", 2),
    ("Sunil Batra",     "+917766554403", "A", 3),
    ("Kavya Shetty",    "+916655443304", "A", 4),
    ("Girish Patel",    "+919988776605", "B", 1),
    ("Smita Kulkarni",  "+918877665506", "B", 2),
    ("Rohan Naik",      "+917766554407", "B", 3),
    ("Divyanka Singh",  "+916655443308", "C", 1),
    ("Tarun Pillai",    "+919988776609", "C", 2),
]

MEDICAL = [
    ("Dr. Anitha Varma",  "+919900112233", "A"),
    ("Dr. Rajesh Nair",   "+918800223344", "B"),
]

FRONT_DESK = [
    ("Pooja Kapoor",   "+919123456780"),
    ("Alok Tiwari",    "+918234567891"),
    ("Sunaina Verma",  "+917345678902"),
]

SUPERVISORS = [
    ("Brijesh Mehta",  "+919911223344", "A"),  # Duty Manager
    ("Sheela D'Souza", "+918822334455", "B"),  # Shift Supervisor
]


def _now():
    return datetime.utcnow().isoformat()

def _id():
    return str(uuid.uuid4())


async def get_block_id(db, hotel_id: str, block_code: str):
    """Fetch Firestore block doc id by block_code and hotel_id."""
    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, lambda: list(
        db.collection("blocks").where("hotel_id", "==", hotel_id).where("block_code", "==", block_code).stream()
    ))
    if docs:
        return docs[0].to_dict()["id"]
    return None


async def get_floor_id(db, block_id: str, level: int):
    """Fetch Firestore floor doc id by block_id + level."""
    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, lambda: list(
        db.collection("floors")
        .where("block_id", "==", block_id)
        .stream()
    ))
    for d in docs:
        data = d.to_dict()
        if data.get("level") == level:
            return data["id"]
    return None


async def save_staff(db, staff_doc: dict):
    loop = asyncio.get_event_loop()
    doc_id = staff_doc["id"]
    await loop.run_in_executor(None,
        lambda: db.collection("staff").document(doc_id).set(staff_doc)
    )


async def seed():
    firebase.initialize()
    db = get_db()

    hotel_id = HOTEL_ID
    if not hotel_id:
        print("[ERROR] VENUE_ID not set in .env — run ingest_hotel.py first!")
        return

    print(f"[SEED] Seeding staff for hotel: {hotel_id}\n")

    # ── Security ───────────────────────────────────────────────────
    print("[+] Security Personnel:")
    for name, phone, block_code in SECURITY:
        block_id = await get_block_id(db, hotel_id, block_code)
        doc = {
            "id":               _id(),
            "hotel_id":         hotel_id,
            "name":             name,
            "phone":            phone,
            "role":             "security",
            "block_id":         block_id or "",
            "current_block_id": block_id or "",
            "current_floor_id": "",
            "on_duty":          True,
            "created_at":       _now(),
        }
        await save_staff(db, doc)
        print(f"   Security [{block_code}] {name}  {phone}")

    # ── Floor Wardens ──────────────────────────────────────────────
    print("\n[+] Floor Wardens:")
    for name, phone, block_code, level in WARDENS:
        block_id = await get_block_id(db, hotel_id, block_code)
        floor_id = await get_floor_id(db, block_id, level) if block_id else None
        doc = {
            "id":               _id(),
            "hotel_id":         hotel_id,
            "name":             name,
            "phone":            phone,
            "role":             "warden",
            "block_id":         block_id or "",
            "current_block_id": block_id or "",
            "current_floor_id": floor_id or "",
            "assigned_floor":   level,
            "on_duty":          True,
            "created_at":       _now(),
        }
        await save_staff(db, doc)
        print(f"   Warden [{block_code}/F{level}] {name}  {phone}")

    # ── Medical Staff ──────────────────────────────────────────────
    print("\n[+] Medical Staff:")
    for name, phone, block_code in MEDICAL:
        block_id = await get_block_id(db, hotel_id, block_code)
        doc = {
            "id":               _id(),
            "hotel_id":         hotel_id,
            "name":             name,
            "phone":            phone,
            "role":             "medical",
            "block_id":         block_id or "",
            "current_block_id": block_id or "",
            "current_floor_id": "",
            "on_duty":          True,
            "created_at":       _now(),
        }
        await save_staff(db, doc)
        print(f"   Medical [{block_code}] {name}  {phone}")

    # ── Front Desk ─────────────────────────────────────────────────
    print("\n[+] Front Desk:")
    for name, phone in FRONT_DESK:
        doc = {
            "id":               _id(),
            "hotel_id":         hotel_id,
            "name":             name,
            "phone":            phone,
            "role":             "front_desk",
            "block_id":         "",
            "current_block_id": "",
            "current_floor_id": "",
            "on_duty":          True,
            "created_at":       _now(),
        }
        await save_staff(db, doc)
        print(f"   Front Desk  {name}  {phone}")

    # ── Supervisors ────────────────────────────────────────────────
    print("\n[+] Supervisors / Managers:")
    for name, phone, block_code in SUPERVISORS:
        block_id = await get_block_id(db, hotel_id, block_code)
        doc = {
            "id":               _id(),
            "hotel_id":         hotel_id,
            "name":             name,
            "phone":            phone,
            "role":             "supervisor",
            "block_id":         block_id or "",
            "current_block_id": block_id or "",
            "current_floor_id": "",
            "on_duty":          True,
            "created_at":       _now(),
        }
        await save_staff(db, doc)
        print(f"   Supervisor [{block_code}] {name}  {phone}")

    total = (len(SECURITY) + len(WARDENS) + len(MEDICAL) +
             len(FRONT_DESK) + len(SUPERVISORS))
    print(f"\n{'='*55}")
    print(f"[DONE] {total} staff members written to Firestore!")
    print(f"{'='*55}")
    print(f"\n  You should now see these Firestore collections:")
    print(f"    hotels, blocks, floors, pois, cameras")
    print(f"    room_occupants   <-- guests with phone numbers")
    print(f"    staff            <-- hotel staff just created")
    print(f"    incidents        (created when ARIA raises an alert)")
    print(f"    dispatches       (created when staff is dispatched)")
    print()


if __name__ == "__main__":
    asyncio.run(seed())
