"""
app/vision/camera_worker.py
────────────────────────────
RTSP camera worker. Reads frames from an RTSP stream,
runs YOLO inference, and feeds detections into the vision pipeline.

One CameraWorker per active camera is created by CameraManager at startup.
"""

import asyncio
from datetime import datetime
from app.vision.schemas import FrameDetection, BoundingBox
from app.vision.pipeline_state import VisionPipelineState
from app.vision.pipeline import vision_pipeline

# YOLOv8 and cv2 will be imported lazily inside _run_sync to prevent startup hangs.
_yolo_available = True  # We assume available if we try to import it
_cv2_available = True


INFERENCE_INTERVAL = 1.0   # seconds between frame reads
FRAME_SKIP         = 5     # process every Nth frame to reduce load
CONFIDENCE_THRESH  = 0.45


class CameraWorker:
    """
    Async worker that reads frames from an RTSP stream and processes threats.

    Args:
        camera_id  — Firestore document ID
        stream_url — rtsp://... or local file path for testing
        venue_id   — Passed through to the vision pipeline state
        model_path — Path to YOLOv8 .pt weights file
    """

    def __init__(
        self,
        camera_id:    str,
        stream_url:   str,
        venue_id:     str,
        shared_model  = None,   # Pre-loaded YOLO model (injected by CameraManager)
    ):
        self.camera_id    = camera_id
        self.stream_url   = stream_url
        self.venue_id     = venue_id
        self._model       = shared_model
        self._stop        = asyncio.Event()

    async def start(self):
        """Start the inference loop in the thread pool executor."""
        self._stop.clear()
        loop = asyncio.get_event_loop()
        # Fire and forget into the executor pool
        loop.run_in_executor(None, self._run_sync)

    def _run_sync(self):
        """Blocking loop — runs in thread pool executor."""
        try:
            import cv2
            from ultralytics import YOLO
        except ImportError:
            print(f"[VISION] {self.camera_id[:8]}: running in NO-OP stub mode (cv2/yolo missing)")
            return

        if self._model is None:
            print(f"[VISION] {self.camera_id[:8]}: no model available — skipping")
            return

        # Firestore stores stream_url as a string.
        # "0", "1", etc. → integer device index for cv2.VideoCapture (webcam).
        source = int(self.stream_url) if self.stream_url.isdigit() else self.stream_url
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"[VISION] Stream unavailable (RTSP offline?): {self.stream_url}")
            return

        frame_count = 0
        print(f"[VISION] Camera {self.camera_id[:8]} started — {self.stream_url}")

        while not self._stop.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"[VISION] Stream ended or error: {self.camera_id[:8]}")
                break

            frame_count += 1
            if frame_count % FRAME_SKIP != 0:
                continue

            h, w = frame.shape[:2]
            results = self._model.predict(
                frame,
                conf=CONFIDENCE_THRESH,
                verbose=False,
            )

            boxes: list[BoundingBox] = []
            for r in results:
                for box in r.boxes:
                    cls_name = r.names[int(box.cls[0])]
                    boxes.append(BoundingBox(
                        x1=float(box.xyxyn[0][0]),
                        y1=float(box.xyxyn[0][1]),
                        x2=float(box.xyxyn[0][2]),
                        y2=float(box.xyxyn[0][3]),
                        confidence=float(box.conf[0]),
                        class_name=cls_name,
                    ))

            if not boxes:
                continue

            detection = FrameDetection(
                camera_id    = self.camera_id,
                frame_ts     = datetime.utcnow().isoformat(),
                boxes        = boxes,
                frame_width  = w,
                frame_height = h,
            )

            # Dispatch to async vision pipeline via asyncio
            initial_state = VisionPipelineState(
                raw_detection = detection,
                venue_id      = self.venue_id,
            )
            asyncio.run_coroutine_threadsafe(
                vision_pipeline.ainvoke(initial_state),
                asyncio.get_event_loop(),
            )

        cap.release()
        print(f"[VISION] Camera {self.camera_id[:8]} stopped")

    async def stop(self):
        self._stop.set()
