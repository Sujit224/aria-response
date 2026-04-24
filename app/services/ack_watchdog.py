import asyncio
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import select, and_
import redis.asyncio as aioredis
from app.models.tables import Dispatch, Staff, Incident
from app.db.session import AsyncSessionLocal

REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379")
CHECK_INTERVAL = 15       # seconds between watchdog checks
ACK_TIMEOUT    = 60       # seconds before re-alerting


async def ack_watchdog():
    """
    Runs as a background asyncio task for the lifetime of the FastAPI app.
    Every CHECK_INTERVAL seconds:
      - Finds dispatches where ack_status=PENDING and sent_at < now - 60s
      - Re-publishes the staff alert to Redis
      - Logs the re-alert (does NOT create a new Dispatch row)
    """
    print("[ARIA-WATCHDOG] Started — checking every 15s for unacknowledged dispatches")

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            cutoff = datetime.utcnow() - timedelta(seconds=ACK_TIMEOUT)

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Dispatch, Staff, Incident)
                    .join(Staff,    Dispatch.staff_id    == Staff.id)
                    .join(Incident, Dispatch.incident_id == Incident.id)
                    .where(
                        and_(
                            Dispatch.ack_status == "PENDING",
                            Dispatch.sent_at    <= cutoff,
                            Incident.status     == "active",
                        )
                    )
                )
                rows = result.all()

            if not rows:
                continue

            r = await aioredis.from_url(REDIS_URL, decode_responses=True)

            for dispatch, staff, incident in rows:
                print(
                    f"[ARIA-WATCHDOG] Re-alerting staff {staff.name} "
                    f"for incident {incident.id} (pending {ACK_TIMEOUT}s)"
                )
                await r.publish(
                    f"staff:{incident.hotel_id}",
                    json.dumps({
                        "event": "DISPATCH_REMINDER",
                        "data": {
                            "dispatch_id":   str(dispatch.id),
                            "incident_id":   str(incident.id),
                            "staff_id":      str(staff.id),
                            "staff_name":    staff.name,
                            "message":       dispatch.message_text,
                            "full_location": incident.full_location,
                            "severity":      incident.severity,
                            "pending_since": dispatch.sent_at.isoformat(),
                            "re_alert":      True,
                        },
                    }),
                )

            await r.aclose()

        except asyncio.CancelledError:
            print("[ARIA-WATCHDOG] Stopped.")
            break
        except Exception as e:
            print(f"[ARIA-WATCHDOG] Error: {e}")