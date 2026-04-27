"""
core/alert_queue.py
Saare detectors ke alerts yahan aate hain.
Duplicate alerts filter karta hai (token saving).
LangGraph agent ko signal deta hai.
"""

import time
from app.vision import config


class AlertQueue:
    def __init__(self):
        # {source_type: last_alert_timestamp}
        # Ye track karta hai kab kaunse type ka alert bheja tha
        self.last_alert_time = {}
        self.pending_alerts  = []   # Process hone wale alerts

        print("  [AlertQueue] ✅ Deduplication queue ready")
        print(f"  [AlertQueue] Cooldown settings: {config.ALERT_COOLDOWN_SECONDS}")

    def add(self, alert: dict) -> bool:
        """
        Naya alert aaya - check karo bhejne layak hai ya nahi.

        Deduplication Logic:
        1. Source type nikalo (weapon, smoke, bag, scan)
        2. Pichla alert us type ka kab gaya tha?
        3. Cooldown time se kam? → Duplicate - reject karo
        4. Cooldown time se zyada? → Valid - queue mein daalo

        Return: True agar alert accept hua, False agar reject
        """
        source   = alert.get("source", "unknown")
        det_type = alert.get("type", "UNKNOWN")

        # Source se cooldown category nikalo
        if "weapon" in source:
            cooldown_key = "weapon"
        elif "smoke" in source:
            cooldown_key = "smoke"
        elif "bag" in source:
            cooldown_key = "bag"
        elif "scan" in source:
            cooldown_key = "scan"
        else:
            cooldown_key = "weapon"   # Default

        cooldown = config.ALERT_COOLDOWN_SECONDS.get(cooldown_key, 60)
        now      = time.time()
        last     = self.last_alert_time.get(cooldown_key, 0)

        # ── DEDUPLICATION CHECK ──
        if (now - last) < cooldown:
            remaining = int(cooldown - (now - last))
            print(f"  [Queue] ⏭ DUPLICATE skipped: {det_type} | Cooldown: {remaining}s baki")
            return False

        # Valid alert - queue mein daalo
        alert["queued_at"] = now
        self.pending_alerts.append(alert)
        self.last_alert_time[cooldown_key] = now

        print(f"  [Queue] ✅ Alert accepted: {det_type} from {source}")
        return True

    def get_next(self) -> dict | None:
        """Queue se agla alert nikalo"""
        if self.pending_alerts:
            return self.pending_alerts.pop(0)
        return None

    def has_pending(self) -> bool:
        return len(self.pending_alerts) > 0
