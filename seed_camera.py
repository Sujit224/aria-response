import asyncio
from app.db.firebase import initialize, get_db

async def check_cameras():
    initialize()
    db = get_db()
    docs = db.collection("cameras").stream()
    found = False
    for doc in docs:
        found = True
        print(f"Camera ID: {doc.id}, Data: {doc.to_dict()}")
    
    if not found:
        print("No cameras found in Firestore. Adding a test camera...")
        # Add a test camera (using webcam '0' or a dummy URL)
        db.collection("cameras").document("test-cam-001").set({
            "id": "test-cam-001",
            "name": "Front Desk Camera",
            "stream_url": "0",  # Default webcam
            "active": True,
            "venue_id": "d6d3d153-5b43-478f-8805-f46ac29abea3"
        })
        print("Added test-cam-001 (webcam source 0)")

if __name__ == "__main__":
    asyncio.run(check_cameras())
