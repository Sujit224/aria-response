import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import app.db.firebase as firebase
firebase.initialize()

from app.vision.pipeline import vision_pipeline
from app.vision.pipeline_state import VisionPipelineState
from app.vision.schemas import FrameDetection, BoundingBox

async def simulate():
    venue_id = os.getenv("VENUE_ID", "d6d3d153-5b43-478f-8805-f46ac29abea3")
    
    # Simulate a "weapon" detection in a specific area
    # Note: room_id/camera_id should exist in your Firestore for best results
    detection = FrameDetection(
        camera_id = "test-cam-001",
        frame_ts  = datetime.utcnow().isoformat(),
        boxes = [
            BoundingBox(
                x1=0.1, y1=0.1, x2=0.3, y2=0.3,
                confidence=0.92,
                class_name="weapon"
            )
        ],
        frame_width=1280,
        frame_height=720
    )
    
    state = VisionPipelineState(
        raw_detection = detection,
        venue_id      = venue_id
    )
    
    print(f"Simulating detection: {detection.boxes[0].class_name} at {detection.camera_id}...")
    await vision_pipeline.ainvoke(state)
    print("Simulation complete. Check the Staff Dashboard!")

if __name__ == "__main__":
    asyncio.run(simulate())
