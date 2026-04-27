from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.collections import (
    get_on_duty_staff,
    update_staff_location,
    get_pending_dispatches,
)

router = APIRouter(prefix="/staff", tags=["staff"])


class LocationUpdate(BaseModel):
    floor_id: str
    block_id: str


@router.get("/on-duty")
async def get_on_duty(hotel_id: str):
    """Returns all on-duty staff with current floor + block."""
    return await get_on_duty_staff(hotel_id)


@router.patch("/{staff_id}/location")
async def update_location(staff_id: str, body: LocationUpdate):
    """Staff device heartbeat — updates current floor + block in Firestore."""
    await update_staff_location(staff_id, body.floor_id, body.block_id)
    return {"status": "updated", "staff_id": staff_id}


@router.get("/dispatches/pending")
async def pending_dispatches(hotel_id: str):
    """
    Returns all PENDING dispatches for this venue.
    Dashboard flashes rows in yellow if pending > 60s.
    """
    rows = await get_pending_dispatches(hotel_id)
    from datetime import datetime
    now = datetime.utcnow()
    return [
        {
            "dispatch_id":   r["id"],
            "incident_id":   r["incident_id"],
            "staff_id":      r["staff_id"],
            "full_location": r.get("_incident", {}).get("full_location", ""),
            "severity":      r.get("_incident", {}).get("severity", ""),
            "sent_at":       r["sent_at"],
            "pending_secs":  int((now - datetime.fromisoformat(r["sent_at"])).total_seconds()),
            "overdue":       (now - datetime.fromisoformat(r["sent_at"])).total_seconds() > 60,
        }
        for r in rows
    ]