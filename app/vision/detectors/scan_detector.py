"""
detectors/scan_detector.py
Model: scan_model.pt (X-ray/scanner trained model)
Status: DORMANT by default - SCANNER_CONNECTED = False in config
Trigger: Weapon class detected in scanned image + confidence >= 0.65
Input: Scanner device ka image folder (camera nahi)
"""

import os
import time
from ultralytics import YOLO
from app.vision import config


class ScanDetector:
    def __init__(self):
        # ── DEVICE CHECK - Sabse pehle ──
        if not config.SCANNER_CONNECTED:
            print("  [Scanner] 💤 DORMANT - Scanner not connected (SCANNER_CONNECTED=False)")
            print("  [Scanner]    config.py mein SCANNER_CONNECTED=True karo jab scanner lagao")
            self.active = False
            self.model  = None
            return

        # Scanner connected hai - model load karo
        print("  [Scanner] Scanner connected! Model load ho raha hai...")
        self.model   = YOLO(config.MODELS["scan"])
        self.thresh  = config.CONFIDENCE["scan"]
        self.trigger_classes = [c.lower() for c in config.SCAN_TRIGGER_CLASSES]
        self.active  = True

        # Processed files track karo (same file dobara process na ho)
        self.processed_files = set()

        # Scanner input folder create karo agar nahi hai
        os.makedirs(config.SCANNER_INPUT_FOLDER, exist_ok=True)

        print(f"  [Scanner] ✅ Ready | Watching folder: {config.SCANNER_INPUT_FOLDER}")
        print(f"  [Scanner] Watching classes: {self.trigger_classes}")

    def process_folder(self) -> dict | None:
        """
        Scanner input folder mein nai images check karo.
        Camera frame nahi - scanner folder ko monitor karta hai.

        Logic:
        1. SCANNER_CONNECTED? Nahi → turant None return karo
        2. Folder mein nai image hai?
        3. YOLO run karo us image par
        4. Weapon class mili + confidence >= 0.65?
        5. Haan → Alert return karo
        """
        if not self.active:
            return None

        # Nai images dhundo folder mein
        for filename in os.listdir(config.SCANNER_INPUT_FOLDER):
            if filename in self.processed_files:
                continue   # Already process ho chuki hai

            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                continue   # Image nahi hai

            image_path = os.path.join(config.SCANNER_INPUT_FOLDER, filename)

            # File abhi bhi write ho rahi hai? Wait karo
            try:
                size1 = os.path.getsize(image_path)
                time.sleep(0.1)
                size2 = os.path.getsize(image_path)
                if size1 != size2:
                    continue   # Still writing
            except Exception:
                continue

            self.processed_files.add(filename)
            print(f"  [Scanner] 🖼 New scan image: {filename}")

            # YOLO run karo
            results = self.model(image_path, conf=self.thresh, verbose=False)[0]

            for box in results.boxes:
                confidence = float(box.conf[0])
                class_id   = int(box.cls[0])
                class_name = self.model.names[class_id].lower()

                # ── TRIGGER CHECK ──
                # Condition 1: Weapon class hai?
                # Condition 2: Confidence >= 0.65?
                if class_name in self.trigger_classes and confidence >= self.thresh:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    print(f"  🚨 SCANNER ALERT: {class_name} | Conf: {confidence:.2f} | File: {filename}")

                    return {
                        "source"     : "scan_detector",
                        "type"       : f"SCANNER_{class_name.upper()}",
                        "confidence" : round(confidence, 2),
                        "location"   : "Scanner-Gate",
                        "image_file" : filename,
                        "bbox"       : [int(x1), int(y1), int(x2), int(y2)],
                        "priority"   : "CRITICAL"
                    }

        return None   # Koi weapon nahi mili

    def process(self, frame=None) -> dict | None:
        """
        main.py ke saath compatible interface.
        Scanner camera frame nahi leta - folder se leta hai.
        """
        return self.process_folder()
