"""
core/logger.py
Saare threat alerts ek log file mein save karo.
Console par bhi clearly dikhao.
"""

import os
from datetime import datetime
from app.vision import config


class ThreatLogger:
    def __init__(self):
        if config.ENABLE_LOGGING:
            os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
            print(f"  [Logger] ✅ Logging to: {config.LOG_FILE}")
        else:
            print(f"  [Logger] Logging disabled")

    def log(self, alert: dict, threat_result: dict):
        """
        Alert + LLM result dono ko log karo.
        Console pe bhi print karo clearly.
        """
        level   = threat_result.get("threat_level", "UNKNOWN")
        message = threat_result.get("threat_message", "")
        action  = threat_result.get("action_required", "")
        ts      = threat_result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # ── Console Output ──
        separator = "═" * 60
        print(f"\n{separator}")
        print(f"  🚨 THREAT ALERT [{level}]")
        print(f"  Time    : {ts}")
        print(f"  Source  : {alert.get('source', 'unknown')}")
        print(f"  Type    : {alert.get('type', 'unknown')}")
        print(f"  Conf    : {alert.get('confidence', 0):.0%}")
        print(f"  Location: {alert.get('location', 'unknown')}")
        print(f"  Message : {message}")
        print(f"  Action  : {action}")
        print(f"{separator}\n")

        # ── File Log ──
        if config.ENABLE_LOGGING:
            try:
                with open(config.LOG_FILE, "a") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"TIMESTAMP : {ts}\n")
                    f.write(f"LEVEL     : {level}\n")
                    f.write(f"SOURCE    : {alert.get('source')}\n")
                    f.write(f"TYPE      : {alert.get('type')}\n")
                    f.write(f"CONFIDENCE: {alert.get('confidence', 0):.0%}\n")
                    f.write(f"LOCATION  : {alert.get('location')}\n")
                    f.write(f"MESSAGE   : {message}\n")
                    f.write(f"ACTION    : {action}\n")
            except Exception as e:
                print(f"  [Logger] ⚠ Log write failed: {e}")
