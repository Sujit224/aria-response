"""
detectors/weapon_detector.py
Notebook: danger-place-detection (Roboflow)
Classes: gun, pistol, rifle, knife, blood, weapon, etc.
Trigger: INSTANT - ek frame mein mili aur confidence >= 0.6 = alert
"""

from ultralytics import YOLO
from app.vision import config


class WeaponDetector:
    def __init__(self):
        print("  [Weapon] Model load ho raha hai...")
        self.model  = YOLO(config.MODELS["weapon"])
        self.thresh = config.CONFIDENCE["weapon"]
        self.trigger_classes = [c.lower() for c in config.WEAPON_TRIGGER_CLASSES]
        print(f"  [Weapon] ✅ Ready | Threshold: {self.thresh}")
        print(f"  [Weapon] Watching: {self.trigger_classes}")

    def process(self, frame) -> dict | None:
        """
        Frame process karo.
        Return: Alert dict agar weapon mili, warna None

        Logic:
        1. YOLO run karo frame par
        2. Har detection ke liye:
           a. Class name check karo - trigger list mein hai?
           b. Confidence check karo - >= 0.6?
           c. Dono pass? → Alert return karo
        3. Koi match nahi? → None return karo
        """
        results = self.model(frame, conf=self.thresh, verbose=False)[0]

        for box in results.boxes:
            confidence  = float(box.conf[0])
            class_id    = int(box.cls[0])
            class_name  = self.model.names[class_id].lower()

            # ── TRIGGER CHECK ──
            # Condition 1: Class hamare trigger list mein hai?
            # Condition 2: Confidence >= threshold?
            if class_name in self.trigger_classes and confidence >= self.thresh:

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                # Frame mein location estimate
                fh, fw = frame.shape[:2]
                loc_x = "Left"   if cx < fw // 3 else ("Right"  if cx > 2 * fw // 3 else "Center")
                loc_y = "Top"    if cy < fh // 3 else ("Bottom" if cy > 2 * fh // 3 else "Middle")

                print(f"  🔫 WEAPON DETECTED: {class_name} | Conf: {confidence:.2f} | Loc: {loc_y}-{loc_x}")

                # Pehla match hi return karo (most confident detection)
                return {
                    "source"    : "weapon_detector",
                    "type"      : class_name.upper(),
                    "confidence": round(confidence, 2),
                    "location"  : f"{loc_y}-{loc_x}",
                    "bbox"      : [int(x1), int(y1), int(x2), int(y2)],
                    "priority"  : "CRITICAL"
                }

        return None   # Koi weapon nahi mili

    def draw(self, frame, alert: dict):
        """Frame par red box aur label draw karo"""
        if not alert:
            return frame
        x1, y1, x2, y2 = alert["bbox"]
        label = f"⚠ {alert['type']} {alert['confidence']:.0%}"
        import cv2
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame
