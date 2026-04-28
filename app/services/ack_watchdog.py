import asyncio
from datetime import datetime, timedelta
from app.db.collections import get_pending_dispatches, publish_staff_event


CHECK_INTERVAL = 15   # seconds
ACK_TIMEOUT    = 60   # seconds before re-alerting


async def ack_watchdog():
    """
    Runs as a background asyncio task for the lifetime of the FastAPI app.
    Every CHECK_INTERVAL seconds:
      - Queries Firestore dispatches where ack_status=PENDING
      - For any dispatch older than ACK_TIMEOUT, re-publishes a DISPATCH_REMINDER
        to the venue's staff_events channel (Firestore, picked up by WS handler)
    """
    print("[ARIA-WATCHDOG] Started — checking every 15s for unacknowledged dispatches")

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            # We don't have a hotel_id at this level, so query all hotels.
            # In production, run one watchdog per active venue.
            import os
            hotel_id = os.getenv("VENUE_ID", "")
            if not hotel_id:
                continue

            rows = await get_pending_dispatches(hotel_id)
            now  = datetime.utcnow()

            for row in rows:
                last_reminded = row.get("last_reminded_at", row["sent_at"])
                sent_at = datetime.fromisoformat(last_reminded)
                if (now - sent_at).total_seconds() < ACK_TIMEOUT:
                    continue

                inc = row.get("_incident", {})
                print(
                    f"[ARIA-WATCHDOG] Re-alerting staff {row['staff_id'][:8]} "
                    f"for incident {row['incident_id'][:8]} (pending >{ACK_TIMEOUT}s)"
                )

                # Update the dispatch so we wait another ACK_TIMEOUT before alerting again
                from app.db.firebase import get_db
                from app.db.collections import _run
                db = get_db()
                await _run(lambda r=row, n=now: db.collection("dispatches").document(r["id"]).update({
                    "last_reminded_at": n.isoformat()
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
                        },
                    }
                )

        except asyncio.CancelledError:
            print("[ARIA-WATCHDOG] Stopped.")
            break
        except Exception as e:
            print(f"[ARIA-WATCHDOG] Error: {e}")