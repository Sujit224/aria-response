"""
app/vision/camera_manager.py
──────────────────────────────
Manages the lifecycle of all active CameraWorker instances for a venue.
Started in FastAPI lifespan. Queries Firestore for active cameras on startup.
"""

import asyncio
from app.db.firebase import get_db
from app.vision.camera_worker import CameraWorker


class CameraManager:
    def __init__(self, venue_id: str, model_path: str = "yolov8n.pt"):
        self.venue_id   = venue_id
        self.model_path = model_path
        self._workers:  list[CameraWorker] = []
        self._tasks:    list[asyncio.Task] = []

    async def start(self):
        """
        Loads all active cameras from Firestore and spawns a CameraWorker per camera.
        Cameras are stored in the 'cameras' collection with 'active' = True.
        """
        db = get_db()
        loop = asyncio.get_event_loop()
        try:
            docs = await loop.run_in_executor(None, lambda: list(
                db.collection("cameras").where("active", "==", True).stream()
            ))
            cameras = [d.to_dict() for d in docs]
            print(f"[VISION] Starting {len(cameras)} camera workers for venue {self.venue_id}")
        except Exception as e:
            print(f"[VISION] Failed to load cameras from Firestore: {e}")
            cameras = []

        for cam in cameras:
            worker = CameraWorker(
                camera_id  = cam["id"],
                stream_url = cam.get("stream_url", ""),
                venue_id   = self.venue_id,
                model_path = self.model_path,
            )
            self._workers.append(worker)
            # Each worker runs in the default thread pool (non-blocking)
            task = asyncio.create_task(worker.start())
            self._tasks.append(task)

    async def stop(self):
        """Signals all workers to stop and waits for them to finish."""
        for worker in self._workers:
            await worker.stop()
        for task in self._tasks:
            task.cancel()
        self._workers.clear()
        self._tasks.clear()
        print(f"[VISION] CameraManager for venue {self.venue_id} stopped")
