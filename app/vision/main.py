"""
main.py  ─  Threat Detector  ─  Main Entry Point
═══════════════════════════════════════════════════

FULL PIPELINE:
  Camera Frame
       │
       ├──► Weapon Detector  (bag_model.pt)
       │         │ confidence >= 0.6 AND class in trigger list?
       │         └──► INSTANT alert → AlertQueue
       │
       ├──► Smoke Detector   (smoke_model.pt)
       │         │ confidence >= 0.6 AND 3 consecutive frames?
       │         └──► alert → AlertQueue
       │
       ├──► Bag Detector     (bag_model.pt + DeepSORT)
       │         │ bag stationary >= 30s AND not already alerted?
       │         └──► alert → AlertQueue
       │
       └──► Scan Detector    (scan_model.pt)  ← DORMANT if SCANNER_CONNECTED=False
                 │ weapon found in scanner folder image?
                 └──► alert → AlertQueue

AlertQueue (deduplication + cooldown filter)
       │
       └──► LangGraph Agent (4 nodes)
                 │ Node1: validate_alert
                 │ Node2: build_prompt
                 │ Node3: call_llm  ← ONLY called when alert passes all checks
                 │ Node4: format_response
                 └──► ThreatLogger (console + file)

KEY RULE:
  LLM sirf tab call hota hai jab:
  1. Detection class trigger list mein ho
  2. Confidence >= 0.6 ho
  3. Detector-specific condition satisfy ho (timer/frames/etc)
  4. AlertQueue cooldown pass ho
  5. LangGraph validate_alert node pass kare
"""

import cv2
import time
import threading
import os
from dotenv import load_dotenv

# Load environment variables (API keys, etc.)
load_dotenv()

from app.vision import config

from app.vision.detectors.weapon_detector import WeaponDetector
from app.vision.detectors.smoke_detector  import SmokeDetector
from app.vision.detectors.bag_detector    import BagDetector
from app.vision.detectors.scan_detector   import ScanDetector
from app.vision.core.alert_queue          import AlertQueue
from app.vision.core.logger               import ThreatLogger
from app.vision.brain.agent               import ThreatAgent
from app.vision.aria_bridge               import ARIABridge


# ══════════════════════════════════════════════════
#  DISPLAY HELPERS
# ══════════════════════════════════════════════════
def draw_status_bar(frame, detectors_status: dict, alert_count: int):
    """Frame ke upar status bar draw karo"""
    h, w = frame.shape[:2]
    # Dark background strip
    cv2.rectangle(frame, (0, 0), (w, 60), (20, 20, 20), -1)

    # Title
    cv2.putText(frame, "THREAT DETECTOR SYSTEM",
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)

    # Status dots
    x_pos = 10
    for name, active in detectors_status.items():
        color = (0, 255, 0) if active else (100, 100, 100)
        cv2.circle(frame, (x_pos, 45), 6, color, -1)
        cv2.putText(frame, name, (x_pos + 12, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        x_pos += 120

    # Alert count
    cv2.putText(frame, f"Alerts: {alert_count}",
                (w - 120, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)


def draw_alert_banner(frame, message: str, level: str):
    """
    Jab alert trigger ho tab frame pe banner dikhao.
    5 seconds tak dikhao.
    """
    h, w  = frame.shape[:2]
    color = (0, 0, 255) if level == "CRITICAL" else (0, 100, 255)

    # Banner background
    cv2.rectangle(frame, (0, h - 70), (w, h), color, -1)
    cv2.putText(frame, f"⚠ [{level}] {message[:80]}",
                (10, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, "SECURITY ALERT - IMMEDIATE ACTION REQUIRED",
                (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 200), 1)
    return frame


# ══════════════════════════════════════════════════
#  ALERT PROCESSOR - Separate thread mein chalega
#  LLM call blocking hai isliye main loop block na ho
# ══════════════════════════════════════════════════
class AlertProcessor(threading.Thread):
    def __init__(self, queue: AlertQueue, agent: ThreatAgent, logger: ThreatLogger, bridge: ARIABridge):
        super().__init__(daemon=True)
        self.queue  = queue
        self.agent  = agent
        self.logger = logger
        self.bridge = bridge

        # Main thread ke saath share karo (display ke liye)
        self.last_threat  = None   # {level, message, action, timestamp}
        self.last_alert_t = 0      # Kab aaya tha last alert
        self.total_alerts = 0

    def run(self):
        """Continuously queue check karo aur alerts process karo"""
        print("  [AlertProcessor] ✅ Background thread started")
        while True:
            if self.queue.has_pending():
                alert = self.queue.get_next()
                if alert:
                    print(f"\n  [AlertProcessor] 🔄 Processing alert: {alert['type']}")

                    # ── LangGraph Agent Call ──
                    # Yahan LLM call hoti hai - sirf tab jab sab conditions satisfy hoon
                    result = self.agent.analyze(alert)

                    if result.get("threat_level") != "INVALID":
                        self.logger.log(alert, result)
                        self.last_threat  = result
                        self.last_alert_t = time.time()
                        self.total_alerts += 1

                        # ── Push to ARIA Firestore pipeline ──
                        # Runs in this background thread (creates its own event loop)
                        self.bridge.dispatch(alert, result)

            time.sleep(0.1)   # CPU ko rest do


# ══════════════════════════════════════════════════
#  MAIN FUNCTION
# ══════════════════════════════════════════════════
def main():
    print("\n" + "═" * 60)
    print("   THREAT DETECTOR SYSTEM  ─  Starting Up")
    print("═" * 60)

    # ── Step 1: Load all detectors ──
    print("\n[1/5] Loading detectors...")
    weapon_det = WeaponDetector()
    smoke_det  = SmokeDetector()
    bag_det    = BagDetector()
    scan_det   = ScanDetector()   # Dormant agar SCANNER_CONNECTED=False
    print("      All detectors loaded ✅")

    # ── Step 2: Setup alert pipeline ──
    print("\n[2/5] Setting up alert pipeline...")
    alert_queue = AlertQueue()
    logger      = ThreatLogger()
    agent       = ThreatAgent()
    bridge      = ARIABridge()
    print("      Pipeline ready ✅")

    # ── Step 3: Start background alert processor ──
    print("\n[3/5] Starting background alert processor...")
    processor = AlertProcessor(alert_queue, agent, logger, bridge)
    processor.start()
    print("      Background thread started ✅")

    # ── Step 4: Open camera ──
    print(f"\n[4/5] Opening video source: {config.VIDEO_SOURCE}")
    cap = cv2.VideoCapture(config.VIDEO_SOURCE)
    if not cap.isOpened():
        print("❌ ERROR: Camera/Video nahi khul raha!")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    print("      Camera ready ✅")

    print("\n[5/5] Starting detection loop...")
    print("      Press Q to quit\n")
    print("─" * 60)

    # ── Detector status for display ──
    detector_status = {
        "Weapon"  : True,
        "Smoke"   : True,
        "Bag"     : True,
        "Scanner" : config.SCANNER_CONNECTED,
    }

    fps_timer   = time.time()
    frame_count = 0

    # ══════════════════════════════════════════════
    #  MAIN DETECTION LOOP
    # ══════════════════════════════════════════════
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera feed lost / Video ended.")
            break

        frame_count += 1

        # ────────────────────────────────────────
        #  EACH DETECTOR INDEPENDENTLY PROCESSES
        #  Same frame teen detectors ko milta hai
        # ────────────────────────────────────────

        # ── Detector 1: Weapon ──
        # Logic: class in trigger_list AND confidence >= 0.6 → INSTANT alert
        weapon_alert = weapon_det.process(frame)
        if weapon_alert:
            accepted = alert_queue.add(weapon_alert)
            if accepted:
                frame = weapon_det.draw(frame, weapon_alert)

        # ── Detector 2: Smoke/Fire ──
        # Logic: class in [fire, smoke] AND confidence >= 0.6
        #        AND 3 consecutive frames → alert
        smoke_alert = smoke_det.process(frame)
        if smoke_alert:
            accepted = alert_queue.add(smoke_alert)
            if accepted:
                frame = smoke_det.draw(frame, smoke_alert)

        # ── Detector 3: Bag (with DeepSORT timer) ──
        # Logic: bag detected → DeepSORT assigns ID
        #        bag stationary >= 30s → alert
        #        same ID ko dobara alert nahi
        bag_alert = bag_det.process(frame)
        if bag_alert:
            alert_queue.add(bag_alert)

        # ── Detector 4: Scanner (Dormant check) ──
        # Logic: SCANNER_CONNECTED=False → instantly returns None
        #        SCANNER_CONNECTED=True → folder se image lo, YOLO run karo
        #        weapon class found AND confidence >= 0.65 → alert
        scan_alert = scan_det.process()
        if scan_alert:
            alert_queue.add(scan_alert)

        # ────────────────────────────────────────
        #  DISPLAY
        # ────────────────────────────────────────
        if config.SHOW_WINDOW:
            # Status bar
            draw_status_bar(frame, detector_status, processor.total_alerts)

            # FPS
            fps = 1.0 / (time.time() - fps_timer + 1e-9)
            fps_timer = time.time()
            cv2.putText(frame, f"FPS: {fps:.1f}",
                        (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # Alert banner - 5 seconds tak dikhao
            if processor.last_threat and (time.time() - processor.last_alert_t) < 5.0:
                frame = draw_alert_banner(
                    frame,
                    processor.last_threat["threat_message"],
                    processor.last_threat["threat_level"]
                )

            cv2.imshow("Threat Detector", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n[Q] Shutting down...")
                break

    # ── Cleanup ──
    cap.release()
    cv2.destroyAllWindows()
    print(f"\n{'═'*60}")
    print(f"  Session ended.")
    print(f"  Total alerts triggered: {processor.total_alerts}")
    print(f"  Log file: {config.LOG_FILE}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
