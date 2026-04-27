"""
detectors/bag_detector.py
Model: bag_model.pt (aapka trained model)
Tracking: DeepSORT - har bag ko unique ID deta hai
Trigger: Bag 30 seconds tak stationary rahe → alert
"""

import time
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from app.vision import config


class BagDetector:
    def __init__(self):
        print("  [Bag] Model load ho raha hai...")
        self.model   = YOLO(config.MODELS["bag"])
        self.thresh  = config.CONFIDENCE["bag"]
        self.tracker = DeepSort(max_age=30, n_init=3)
        self.trigger_classes = [c.lower() for c in config.BAG_TRIGGER_CLASSES]

        # ── DeepSORT Tracking State ──
        self.bag_static_since = {}   # {track_id: timestamp} - kab se ruka hai
        self.bag_last_center  = {}   # {track_id: (cx, cy)}  - pichli position
        self.alert_sent_ids   = set()  # Jinhe alert ja chuka hai

        print(f"  [Bag] ✅ Ready | Threshold: {self.thresh} | Alert after: {config.BAG_STATIC_SECONDS}s")

    def _center(self, bbox):
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    def _moved(self, prev, curr, thresh=20):
        """20 pixels se kam movement = stationary"""
        if prev is None:
            return True
        return np.sqrt((curr[0]-prev[0])**2 + (curr[1]-prev[1])**2) > thresh

    def process(self, frame) -> dict | None:
        """
        Frame process karo.
        Return: Alert dict agar bag 30s se stationary, warna None

        Logic:
        1. YOLO se bags detect karo
        2. DeepSORT se har bag ko unique ID do
        3. Har ID ke liye:
           a. Bag hila? → Timer reset karo
           b. Nahi hila? → Timer badhta raho
        4. Timer >= 30s AND alert nahi gaya?
           → Alert return karo + ID lock karo
        """
        results = self.model(frame, conf=self.thresh, verbose=False)[0]

        # YOLO detections ko DeepSORT format mein convert karo
        detections = []
        for box in results.boxes:
            class_name = self.model.names[int(box.cls[0])].lower()
            if class_name in self.trigger_classes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(([x1, y1, x2-x1, y2-y1], conf, class_name))

        # DeepSORT update
        tracks = self.tracker.update_tracks(detections, frame=frame)
        now    = time.time()

        for track in tracks:
            if not track.is_confirmed():
                continue

            tid    = track.track_id
            bbox   = track.to_ltrb()
            center = self._center(bbox)

            # Pehli baar dikh raha hai?
            if tid not in self.bag_static_since:
                self.bag_static_since[tid] = now
                self.bag_last_center[tid]  = center
                print(f"  🆕 New bag tracked → ID: {tid}")
                continue

            # Movement check
            if self._moved(self.bag_last_center[tid], center):
                self.bag_static_since[tid] = now   # Timer reset
                self.bag_last_center[tid]  = center

            static_time = now - self.bag_static_since[tid]

            # ── TRIGGER CHECK ──
            if static_time >= config.BAG_STATIC_SECONDS and tid not in self.alert_sent_ids:
                self.alert_sent_ids.add(tid)

                fh, fw = frame.shape[:2]
                cx, cy = center
                loc_x = "Left"   if cx < fw // 3 else ("Right"  if cx > 2 * fw // 3 else "Center")
                loc_y = "Top"    if cy < fh // 3 else ("Bottom" if cy > 2 * fh // 3 else "Middle")

                print(f"  ⏱ BAG ALERT: ID:{tid} | {static_time:.0f}s stationary | Loc: {loc_y}-{loc_x}")

                return {
                    "source"        : "bag_detector",
                    "type"          : "ABANDONED_BAG",
                    "track_id"      : tid,
                    "static_seconds": round(static_time),
                    "confidence"    : self.thresh,
                    "location"      : f"{loc_y}-{loc_x}",
                    "bbox"          : [int(v) for v in bbox],
                    "priority"      : "HIGH"
                }

        return None

    def get_active_tracks(self):
        """Main loop ke liye - sab active tracks return karo (display ke liye)"""
        return self.bag_static_since, self.alert_sent_ids

    def draw(self, frame, tracks):
        """Sab active bags draw karo"""
        import cv2
        now = time.time()
        for tid, since in tracks[0].items():
            elapsed  = now - since
            alerted  = tid in tracks[1]
            color    = (0, 0, 255) if alerted else (0, 255, 100) if elapsed < 15 else (0, 165, 255)
            label    = f"Bag ID:{tid} {elapsed:.0f}s {'⚠ ALERT' if alerted else ''}"
            # Note: bbox drawing yahan nahi hoga (tracker se alag pass karna hoga)
        return frame
