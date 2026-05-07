"""
Quick test of the ARIABridge in isolation — simulates what AlertProcessor does
after ThreatAgent.analyze() returns a CRITICAL weapon result.
Run from project root: python test_bridge.py
"""
import app.db.firebase as firebase
firebase.initialize()

from app.vision.aria_bridge import ARIABridge

bridge = ARIABridge()
bridge._initialized = True   # firebase already initialized above

alert = {
    "source":     "weapon_detector",
    "type":       "KNIFE",
    "confidence": 0.83,
    "location":   "Middle-Right",
    "priority":   "CRITICAL",
}

threat_result = {
    "threat_level":    "CRITICAL",
    "threat_message":  "A knife was detected by CCTV at Room 214 — Middle-Right. Immediate threat to safety.",
    "action_required": "Evacuate area and contact armed response unit immediately.",
    "timestamp":       "2026-05-05 14:00:00",
}

print("Dispatching test alert via ARIABridge...")
bridge.dispatch(alert, threat_result)
print("Done — check the Staff Dashboard!")
