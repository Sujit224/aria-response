import asyncio
import os
from firebase_admin import credentials, firestore, initialize_app

cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "secrets/serviceAccount.json")
cred = credentials.Certificate(cred_path)
initialize_app(cred)
db = firestore.client()

async def fix():
    incidents = db.collection("incidents").where("status", "==", "active").stream()
    hotel_id = "25425382-1de9-46f7-8554-d5968ea4f439"
    
    for doc in incidents:
        data = doc.to_dict()
        loc = data.get("full_location", "")
        # Parse "Block A, Room 101, Floor 1"
        if "Block" in loc and "Floor" in loc:
            parts = [p.strip() for p in loc.split(",")]
            block_code = parts[0].replace("Block ", "").strip()
            room_name = parts[1].strip()
            floor_level = int(parts[2].replace("Floor ", "").strip())
            
            # Find block
            blocks = list(db.collection("blocks").where("hotel_id", "==", hotel_id).where("block_code", "==", block_code).stream())
            if not blocks: continue
            block_id = blocks[0].id
            
            # Find floor
            floors = list(db.collection("floors").where("block_id", "==", block_id).where("level", "==", floor_level).stream())
            if not floors: continue
            floor_id = floors[0].id
            
            # Find poi
            pois = list(db.collection("pois").where("floor_id", "==", floor_id).where("name", "==", room_name).stream())
            if not pois: continue
            poi_id = pois[0].id
            
            print(f"Updating incident {doc.id} -> Floor: {floor_id}, POI: {poi_id}")
            doc.reference.update({
                "floor_id": floor_id,
                "origin_poi_id": poi_id
            })

if __name__ == "__main__":
    asyncio.run(fix())
