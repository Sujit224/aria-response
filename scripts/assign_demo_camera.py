"""
scripts/assign_demo_camera.py
─────────────────────────────
Assigns the laptop webcam (stream_url = "0") to ONE randomly-chosen camera
in Firestore. All other camera docs are set to active=False so the worker
only starts a single feed.

After running:
  • One camera doc  → active=True,  stream_url="0"
  • All others      → active=False
  • .env            → VISION_ENABLED=true

Usage:
    python scripts/assign_demo_camera.py
"""

import os
import random
import sys
import uuid
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import app.db.firebase as firebase

STREAM_SOURCE = sys.argv[1] if len(sys.argv) > 1 else "0"

def _now():
    return datetime.datetime.utcnow().isoformat()

def main():
    firebase.initialize()
    db = firebase.get_db()

    print("[*] Fetching cameras from Firestore...")
    docs = list(db.collection("cameras").stream())
    cameras = [(d.id, d.to_dict()) for d in docs]
    print(f"    Found {len(cameras)} camera(s)")

    if not cameras:
        print("[*] No cameras in DB — creating a demo camera doc...")
        floors = list(db.collection("floors").limit(1).stream())
        if not floors:
            print("[!] No floors found in DB either. Run the hotel ingest first.")
            return

        floor_doc  = floors[0].to_dict()
        floor_id   = floor_doc["id"]
        block_id   = floor_doc["block_id"]
        cam_id     = str(uuid.uuid4())

        db.collection("cameras").document(cam_id).set({
            "id":         cam_id,
            "floor_id":   floor_id,
            "block_id":   block_id,
            "coord_x":    12,
            "coord_y":    5,
            "stream_url": STREAM_SOURCE,
            "active":     True,
            "label":      "Demo Webcam — Main Corridor",
            "created_at": _now(),
            "updated_at": _now(),
        })
        print(f"[+] Created demo camera: {cam_id}")
        print(f"    floor_id={floor_id}  stream_url={STREAM_SOURCE!r}")
        _patch_env()
        return

    chosen_id, chosen_data = random.choice(cameras)
    print(f"\n[*] Randomly selected camera: {chosen_id}")
    print(f"    Was: stream_url={chosen_data.get('stream_url')!r}  active={chosen_data.get('active')}")

    print("[*] Updating camera docs in a batch...")
    batch = db.batch()
    for cam_id, cam_data in cameras:
        is_chosen   = (cam_id == chosen_id)
        new_url     = STREAM_SOURCE if is_chosen else cam_data.get("stream_url", "")
        
        doc_ref = db.collection("cameras").document(cam_id)
        batch.update(doc_ref, {
            "active":     is_chosen,
            "stream_url": new_url,
            "updated_at": _now(),
        })
        
        status = "* ACTIVE " if is_chosen else "  inactiv"
        # don't print for every 165 docs, too spammy
        if is_chosen:
            label = cam_data.get("label") or cam_data.get("stream_url", "")
            print(f"    [{status}] {cam_id[:8]}  {label}")

    print("[*] Committing batch to Firestore...")
    batch.commit()

    print(f"\n[OK] Camera {chosen_id[:8]} is now streaming from: {STREAM_SOURCE!r}")
    _patch_env()

def _patch_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_path):
        print(f"[!] .env not found at {env_path} — set VISION_ENABLED=true manually")
        return

    with open(env_path, "r") as f:
        content = f.read()

    if "VISION_ENABLED=true" in content:
        print("[*] .env already has VISION_ENABLED=true — no change needed")
        return

    if "VISION_ENABLED=false" in content:
        content = content.replace("VISION_ENABLED=false", "VISION_ENABLED=true")
    elif "VISION_ENABLED" in content:
        import re
        content = re.sub(r"VISION_ENABLED\s*=\s*\S+", "VISION_ENABLED=true", content)
    else:
        content += "\nVISION_ENABLED=true\n"

    with open(env_path, "w") as f:
        f.write(content)

    print("[*] .env → VISION_ENABLED=true")
    print("\n⚠  Restart uvicorn so the new env takes effect:\n   Ctrl+C then: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()
