"""
detectors/smoke_detector.py
Notebook: smoke-fire-detection-yolo
Classes: ["fire", "smoke"]  ← Exactly notebook ke data.yaml se (nc:2)
Trigger: 3 CONSECUTIVE FRAMES mein dike tab alert
         (False positive rokne ke liye)
"""

from ultralytics import YOLO
from app.vision import config


class SmokeDetector:
    def __init__(self):
        print("  [Smoke] Model load ho raha hai...")
        self.model   = YOLO(config.MODELS["smoke"])
        self.thresh  = config.CONFIDENCE["smoke"]
        self.trigger_classes = [c.lower() for c in config.SMOKE_TRIGGER_CLASSES]

        # ── Consecutive Frame Counter ──
        # Notebook mein nc:2, names: ["fire", "smoke"]
        # Ye dict track karta hai kitne consecutive frames mein dika
        self.consecutive_count = {}   # {"fire": 0, "smoke": 0}

        print(f"  [Smoke] ✅ Ready | Threshold: {self.thresh}")
        print(f"  [Smoke] Watching: {self.trigger_classes}")
        print(f"  [Smoke] Consecutive frames needed: {config.SMOKE_CONSECUTIVE_FRAMES}")

    def process(self, frame) -> dict | None:
        """
        Frame process karo.
        Return: Alert dict agar smoke/fire confirmed, warna None

        Logic (3-frame confirmation):
        1. YOLO run karo
        2. Koi trigger class mili?
           → Haan: us class ka counter +1 karo
           → Nahi: us class ka counter 0 karo (reset)
        3. Counter >= 3?
           → Haan: Alert return karo (confirmed detection)
           → Nahi: None return karo (wait karo)

        Kyun 3 frames?
        → Ek frame mein cloud, dust ya reflection bhi smoke jaisi
          dikh sakti hai. 3 consecutive frames = real hai.
        """
        results = self.model(frame, conf=self.thresh, verbose=False)[0]

        detected_this_frame = set()

        for box in results.boxes:
            confidence = float(box.conf[0])
            class_id   = int(box.cls[0])
            class_name = self.model.names[class_id].lower()

            if class_name in self.trigger_classes and confidence >= self.thresh:
                detected_this_frame.add(class_name)

                # Counter badhao
                self.consecutive_count[class_name] = \
                    self.consecutive_count.get(class_name, 0) + 1

                current_count = self.consecutive_count[class_name]
                print(f"  🔥 {class_name.upper()} seen: frame {current_count}/{config.SMOKE_CONSECUTIVE_FRAMES} | Conf: {confidence:.2f}")

                # ── TRIGGER CHECK ──
                if current_count >= config.SMOKE_CONSECUTIVE_FRAMES:
                    # Confirmed! Counter reset karo dobara spam na ho
                    self.consecutive_count[class_name] = 0

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    fh, fw = frame.shape[:2]
                    loc_x = "Left"   if cx < fw // 3 else ("Right"  if cx > 2 * fw // 3 else "Center")
                    loc_y = "Top"    if cy < fh // 3 else ("Bottom" if cy > 2 * fh // 3 else "Middle")

                    print(f"  🚨 SMOKE/FIRE CONFIRMED after {config.SMOKE_CONSECUTIVE_FRAMES} frames!")

                    return {
                        "source"    : "smoke_detector",
                        "type"      : class_name.upper(),
                        "confidence": round(confidence, 2),
                        "location"  : f"{loc_y}-{loc_x}",
                        "bbox"      : [int(x1), int(y1), int(x2), int(y2)],
                        "priority"  : "CRITICAL"
                    }

        # Jo classes is frame mein nahi dikhein, unka counter reset karo
        for cls in self.trigger_classes:
            if cls not in detected_this_frame:
                if self.consecutive_count.get(cls, 0) > 0:
                    self.consecutive_count[cls] = 0

        return None

    def draw(self, frame, alert: dict):
        """Frame par orange box draw karo"""
        if not alert:
            return frame
        x1, y1, x2, y2 = alert["bbox"]
        label = f"🔥 {alert['type']} {alert['confidence']:.0%}"
        import cv2
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 100, 255), 3)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
        return frame
