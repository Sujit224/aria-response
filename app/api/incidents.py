import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import redis.asyncio as aioredis
from app.db.session import get_db
from app.models.tables import Incident, Dispatch, EmergencyAlert, Floor, Guest, POI
from app.models.schemas import IncomingMessage, PipelineState
from app.graph.pipeline import aria_pipeline
from app.services.pathfinding import reroute

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/active")
async def list_active_incidents(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Staff only — all unresolved incidents with dispatch summary."""
    result = await db.execute(
        select(Incident)
        .where(and_(Incident.hotel_id == hotel_id, Incident.status == "active"))
        .order_by(Incident.detected_at.desc())
    )
    incidents = result.scalars().all()
    out = []
    for inc in incidents:
        dispatch_res = await db.execute(
            select(Dispatch).where(Dispatch.incident_id == inc.id)
        )
        dispatches = dispatch_res.scalars().all()
        out.append({
            "incident_id":   inc.id,
            "type":          inc.type,
            "severity":      inc.severity,
            "status":        inc.status,
            "source":        inc.source,
            "full_location": inc.full_location,
            "detected_at":   inc.detected_at.isoformat(),
            "blocked_nodes": inc.blocked_nodes,
            "dispatches": [
                {
                    "dispatch_id": d.id,
                    "staff_id":    d.staff_id,
                    "ack_status":  d.ack_status,
                    "sent_at":     d.sent_at.isoformat(),
                    "acked_at":    d.acked_at.isoformat() if d.acked_at else None,
                }
                for d in dispatches
            ],
        })
    return out


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Full incident detail — zones, dispatches, alert overlay."""
    inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = inc_res.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    dispatch_res = await db.execute(
        select(Dispatch).where(Dispatch.incident_id == incident_id)
    )
    alert_res = await db.execute(
        select(EmergencyAlert).where(EmergencyAlert.incident_id == incident_id)
    )

    return {
        "incident": {
            "id":            inc.id,
            "type":          inc.type,
            "severity":      inc.severity,
            "status":        inc.status,
            "source":        inc.source,
            "full_location": inc.full_location,
            "blocked_nodes": inc.blocked_nodes,
            "detected_at":   inc.detected_at.isoformat(),
            "resolved_at":   inc.resolved_at.isoformat() if inc.resolved_at else None,
        },
        "dispatches": [
            {
                "id":         d.id,
                "staff_id":   d.staff_id,
                "ack_status": d.ack_status,
                "sent_at":    d.sent_at.isoformat(),
                "acked_at":   d.acked_at.isoformat() if d.acked_at else None,
            }
            for d in dispatch_res.scalars()
        ],
        "alerts": [
            {
                "id":            a.id,
                "floor_id":      a.floor_id,
                "blocked_nodes": a.blocked_nodes,
                "radius":        a.radius,
            }
            for a in alert_res.scalars()
        ],
    }


@router.post("/sos")
async def guest_sos(
    session_id: str,
    venue_id: str,
    room_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Guest panic button — creates an IncomingMessage and runs it through
    the full LangGraph pipeline exactly like a chat message.
    """
    incoming = IncomingMessage(
        session_id = session_id,
        raw_text   = "EMERGENCY — I need immediate help!",
        room_id    = room_id,
        venue_id   = venue_id,
    )
    state = PipelineState(incoming=incoming)
    await aria_pipeline.ainvoke(state)
    return {"status": "sos_triggered", "session_id": session_id}


@router.patch("/{incident_id}/ack")
async def ack_dispatch(
    incident_id: str,
    dispatch_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Staff acknowledges a dispatch. Moves ack_status → ACCEPTED."""
    await db.execute(
        update(Dispatch)
        .where(and_(
            Dispatch.id          == dispatch_id,
            Dispatch.incident_id == incident_id,
        ))
        .values(ack_status="ACCEPTED", acked_at=datetime.utcnow())
    )
    await db.commit()
    return {"status": "acknowledged", "dispatch_id": dispatch_id}


@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    """
    Staff closes the incident:
    - Sets status=resolved
    - Clears blocked_nodes from the incident
    - Publishes INCIDENT_RESOLVED to the venue dashboard channel
    """
    await db.execute(
        update(Incident)
        .where(Incident.id == incident_id)
        .values(
            status       = "resolved",
            blocked_nodes = [],
            resolved_at  = datetime.utcnow(),
        )
    )
    # Clear emergency alerts too
    await db.execute(
        update(EmergencyAlert)
        .where(EmergencyAlert.incident_id == incident_id)
        .values(blocked_nodes=[], radius=0.0)
    )
    await db.commit()

    # Notify all clients
    inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = inc_res.scalar_one_or_none()
    try:
        r = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.publish(
            f"dashboard:{inc.hotel_id}",
            json.dumps({
                "event": "INCIDENT_RESOLVED",
                "data": {"incident_id": incident_id},
            }),
        )
        await r.aclose()
    except Exception:
        pass

    return {"status": "resolved", "incident_id": incident_id}


@router.post("/{incident_id}/reroute")
async def reroute_path(
    incident_id: str,
    guest_session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Called when fire/hazard spreads — re-runs A* with updated blocked_nodes
    and pushes a PATH_UPDATE event to the guest's session.
    Used when new EmergencyAlert rows are inserted as an incident escalates.
    """
    # Load incident
    inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = inc_res.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Load floor grid
    floor_res = await db.execute(select(Floor).where(Floor.id == inc.floor_id))
    floor = floor_res.scalar_one_or_none()
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    # Load all blocked nodes from emergency alerts on this floor
    alert_res = await db.execute(
        select(EmergencyAlert).where(EmergencyAlert.incident_id == incident_id)
    )
    all_blocked = []
    for alert in alert_res.scalars():
        all_blocked.extend(alert.blocked_nodes or [])

    # Get guest position from session
    guest_res = await db.execute(
        select(Guest).where(Guest.session_id == guest_session_id)
    )
    guest = guest_res.scalar_one_or_none()
    if not guest or not guest.poi_id:
        raise HTTPException(status_code=404, detail="Guest location unknown")

    poi_res = await db.execute(select(POI).where(POI.id == guest.poi_id))
    poi = poi_res.scalar_one_or_none()

    # Find nearest safe exit (re-calculate ignoring blocked ones)
    exit_res = await db.execute(
        select(POI).where(and_(POI.floor_id == floor.id, POI.is_safe_exit == True))
    )
    exits = exit_res.scalars().all()
    blocked_set = set(map(tuple, [list(b) for b in all_blocked]))
    valid_exits = [e for e in exits if (e.coord_x, e.coord_y) not in blocked_set]
    if not valid_exits:
        valid_exits = exits  # fallback — all exits blocked is edge case

    nearest_exit = min(
        valid_exits,
        key=lambda e: abs(e.coord_x - poi.coord_x) + abs(e.coord_y - poi.coord_y),
    )

    new_path = reroute(
        grid          = floor.static_grid,
        guest_pos     = (poi.coord_x, poi.coord_y),
        exit_pos      = (nearest_exit.coord_x, nearest_exit.coord_y),
        blocked_nodes = all_blocked,
    )

    try:
        r = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.publish(
            f"session:{guest_session_id}",
            json.dumps({
                "event": "PATH_UPDATE",
                "data": {
                    "incident_id":   incident_id,
                    "path_update":   new_path,
                    "blocked_nodes": all_blocked,
                },
            }),
        )
        await r.aclose()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis publish failed: {e}")

    return {"path_length": len(new_path), "new_path": new_path}