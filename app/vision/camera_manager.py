"""
app/vision/camera_manager.py
──────────────────────────────
Manages the lifecycle of all active CameraWorker instances for a venue.
Started in FastAPI lifespan. Queries Firestore for active cameras on startup.
"""

import asyncio
from app.db.firebase import get_db
from app.vision.camera_worker import CameraWorker, _yolo_available

# Load the YOLO model ONCE and share it across all workers.
# This prevents N×model-load spam when many cameras are active.
_shared_model = None

def _get_shared_model(model_path: str):
    global _shared_model
    if _shared_model is None and _yolo_available:
        try:
            from ultralytics import YOLO
            _shared_model = YOLO(model_path)
            _shared_model.fuse()
            print(f"[VISION] Shared YOLO model loaded: {model_path}")
        except Exception as e:
            print(f"[VISION] Failed to load YOLO model: {e}")
    return _shared_model


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
                db.collection("cameras")
                  .where(filter=("active", "==", True))
                  .stream()
            ))
            cameras = [d.to_dict() for d in docs]
            print(f"[VISION] Found {len(cameras)} active camera(s) for venue {self.venue_id}")
        except Exception as e:
            print(f"[VISION] Failed to load cameras from Firestore: {e}")
            cameras = []

        if not cameras:
            print("[VISION] No active cameras — workers skipped")
            return

        # Load the model once, share it across all workers
        shared_model = _get_shared_model(self.model_path)

        for cam in cameras:
            stream_url = cam.get("stream_url", "")
            if not stream_url:
                print(f"[VISION] Camera {cam.get('id', '?')[:8]} has no stream_url — skipped")
                continue
            worker = CameraWorker(
                camera_id    = cam["id"],
                stream_url   = stream_url,
                venue_id     = self.venue_id,
                shared_model = shared_model,
            )
            self._workers.append(worker)
            task = asyncio.create_task(worker.start())
            self._tasks.append(task)

        print(f"[VISION] Started {len(self._workers)} worker(s)")

    async def stop(self):
        """Signals all workers to stop and waits for them to finish."""
        for worker in self._workers:
            await worker.stop()
        for task in self._tasks:
            task.cancel()
        self._workers.clear()
        self._tasks.clear()
        print(f"[VISION] CameraManager for venue {self.venue_id} stopped")
