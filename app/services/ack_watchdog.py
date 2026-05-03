import asyncio
from datetime import datetime, timedelta
from app.db.collections import get_pending_dispatches, publish_staff_event


CHECK_INTERVAL = 15   # seconds

async def ack_watchdog():
    """
    Runs as a background asyncio task for the lifetime of the FastAPI app.
    """
    # Configurable limits
    ACK_TIMEOUT_VAL    = 60   # Seconds before re-alerting
    MAX_REMINDERS      = 5    # Stop re-alerting after this many attempts

    print(f"[ARIA-WATCHDOG] Started — checking every {CHECK_INTERVAL}s for unacknowledged dispatches")

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            import os
            hotel_id = os.getenv("VENUE_ID", "")
            if not hotel_id:
                continue

            rows = await get_pending_dispatches(hotel_id)
            now  = datetime.utcnow()

            for row in rows:
                last_reminded = row.get("last_reminded_at", row["sent_at"])
                sent_at       = datetime.fromisoformat(last_reminded)
                reminder_count = row.get("reminder_count", 0)

                age = (now - sent_at).total_seconds()
                if age < ACK_TIMEOUT_VAL:
                    continue

                if reminder_count >= MAX_REMINDERS:
                    # Too many reminders, stop alerting for this one
                    continue

                inc = row.get("_incident", {})
                new_count = reminder_count + 1
                
                print(
                    f"[ARIA-WATCHDOG] Re-alerting staff {row['staff_id'][:8]} "
                    f"for incident {row['incident_id'][:8]} (pending {int(age)}s, attempt {new_count})"
                )

                # Update the dispatch
                from app.db.firebase import get_db
                from app.db.collections import _run
                db = get_db()
                await _run(lambda r=row, n=now, c=new_count: db.collection("dispatches").document(r["id"]).update({
                    "last_reminded_at": n.isoformat(),
                    "reminder_count": c
                }))

                await publish_staff_event(
                    hotel_id,
                    {
                        "event": "DISPATCH_REMINDER",
                        "data": {
                            "dispatch_id":   row["id"],
                            "incident_id":   row["incident_id"],
                            "staff_id":      row["staff_id"],
                            "message":       row.get("message_text", ""),
                            "full_location": inc.get("full_location", ""),
                            "severity":      inc.get("severity", ""),
                            "pending_since": row["sent_at"],
                            "re_alert":      True,
                            "attempt":       new_count
                        },
                    }
                )

        except asyncio.CancelledError:
            print("[ARIA-WATCHDOG] Stopped.")
            break
        except Exception as e:
            print(f"[ARIA-WATCHDOG] Error: {e}")