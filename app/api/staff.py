from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from pydantic import BaseModel
from app.db.session import get_db
from app.models.tables import Staff, Dispatch, Incident

router = APIRouter(prefix="/staff", tags=["staff"])


class LocationUpdate(BaseModel):
    floor_id: str
    block_id: str


@router.get("/on-duty")
async def get_on_duty_staff(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Returns all on-duty staff with current floor + block — used by zone resolver."""
    result = await db.execute(
        select(Staff).where(
            and_(Staff.hotel_id == hotel_id, Staff.on_duty == True)
        )
    )
    staff = result.scalars().all()
    return [
        {
            "staff_id":        s.id,
            "name":            s.name,
            "role":            s.role,
            "current_status":  s.current_status,
            "current_floor_id": str(s.current_floor_id) if s.current_floor_id else None,
            "current_block_id": str(s.current_block_id) if s.current_block_id else None,
        }
        for s in staff
    ]


@router.patch("/{staff_id}/location")
async def update_staff_location(
    staff_id: str,
    body: LocationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Staff device heartbeat — updates current floor + block.
    Zone resolver queries this to find on-duty staff near an incident.
    Called every 30s from the staff dashboard.
    """
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    await db.execute(
        update(Staff)
        .where(Staff.id == staff_id)
        .values(
            current_floor_id = body.floor_id,
            current_block_id = body.block_id,
        )
    )
    await db.commit()
    return {"status": "updated", "staff_id": staff_id}


@router.get("/dispatches/pending")
async def get_pending_dispatches(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns all PENDING dispatches for the ack watchdog and staff dashboard.
    Dashboard flashes rows in yellow if pending > 60s.
    """
    result = await db.execute(
        select(Dispatch, Staff, Incident)
        .join(Staff,    Dispatch.staff_id    == Staff.id)
        .join(Incident, Dispatch.incident_id == Incident.id)
        .where(
            and_(
                Incident.hotel_id   == hotel_id,
                Dispatch.ack_status == "PENDING",
                Incident.status     == "active",
            )
        )
        .order_by(Dispatch.sent_at.asc())
    )
    rows = result.all()
    now = datetime.utcnow()
    return [
        {
            "dispatch_id":   str(d.id),
            "incident_id":   str(i.id),
            "staff_id":      str(s.id),
            "staff_name":    s.name,
            "full_location": i.full_location,
            "severity":      i.severity,
            "sent_at":       d.sent_at.isoformat(),
            "pending_secs":  int((now - d.sent_at).total_seconds()),
            "overdue":       (now - d.sent_at).total_seconds() > 60,
        }
        for d, s, i in rows
    ]