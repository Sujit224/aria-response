import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.db.collections import (
    list_active_incidents, get_incident,
    get_dispatches_for_incident, get_alerts_for_incident,
    update_incident_status, ack_dispatch,
    publish_session_event, publish_dashboard_event,
)
from app.models.schemas import IncomingMessage, PipelineState
from app.graph.pipeline import aria_pipeline
from app.services.pathfinding import reroute, astar, get_nearest_unblocked_exit, get_nearest_blocked_exit
from app.db.collections import (
    get_floor, get_pois_on_floor, get_exits_on_floor,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/active")
async def list_active(hotel_id: str):
    """Staff only — all unresolved incidents with dispatch summary."""
    incidents = await list_active_incidents(hotel_id)
    result = []
    for inc in incidents:
        dispatches = await get_dispatches_for_incident(inc["id"])
        result.append({**inc, "dispatches": dispatches})
    return result


@router.get("/{incident_id}")
async def get_one(incident_id: str):
    """Full incident detail — zones, dispatches, alert overlay."""
    inc = await get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    dispatches = await get_dispatches_for_incident(incident_id)
    alerts     = await get_alerts_for_incident(incident_id)
    return {"incident": inc, "dispatches": dispatches, "alerts": alerts}


@router.post("/sos")
async def guest_sos(session_id: str, venue_id: str, room_id: str):
    """Guest panic button — runs full LangGraph pipeline."""
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
async def ack(incident_id: str, dispatch_id: str):
    """Staff acknowledges a dispatch — sets ack_status → ACCEPTED in Firestore."""
    await ack_dispatch(dispatch_id)
    return {"status": "acknowledged", "dispatch_id": dispatch_id}


@router.post("/{incident_id}/resolve")
async def resolve(incident_id: str):
    """
    Staff resolves the incident:
    - Sets status=resolved in Firestore
    - Publishes INCIDENT_RESOLVED to dashboard channel
    """
    inc = await get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    await update_incident_status(incident_id, "resolved")
    await publish_dashboard_event(
        inc["hotel_id"],
        {"event": "INCIDENT_RESOLVED", "data": {"incident_id": incident_id}},
    )
    return {"status": "resolved", "incident_id": incident_id}


@router.post("/{incident_id}/reroute")
async def reroute_path(incident_id: str, guest_session_id: str):
    """
    Re-runs A* with updated blocked_nodes when hazard spreads,
    then publishes PATH_UPDATE to the guest's Firestore session channel.
    """
    inc = await get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    floor = await get_floor(inc["floor_id"])
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    alerts = await get_alerts_for_incident(incident_id)
    all_blocked = []
    for alert in alerts:
        all_blocked.extend(alert.get("blocked_nodes", []))

    exits = await get_exits_on_floor(inc["floor_id"])
    pois  = await get_pois_on_floor(inc["floor_id"])

    origin_poi = next((p for p in pois if p["id"] == inc.get("origin_poi_id")), None)
    if not origin_poi:
        raise HTTPException(status_code=404, detail="Guest location unknown")

    blocked_set = {(b[0], b[1]) for b in all_blocked}
    
    nearest_exit = get_nearest_unblocked_exit(exits, gx, gy, blocked_set)
    danger_exit = get_nearest_blocked_exit(exits, gx, gy, blocked_set)

    new_path = reroute(
        grid          = floor["static_grid"],
        guest_pos     = (gx, gy),
        exit_pos      = (nearest_exit["coord_x"], nearest_exit["coord_y"]),
        blocked_nodes = all_blocked,
    )

    danger_path = []
    if danger_exit:
        dpath = astar(
            grid    = floor["static_grid"],
            start   = (gx, gy),
            end     = (danger_exit["coord_x"], danger_exit["coord_y"]),
            blocked = [],
        )
        danger_path = [[p[0], p[1]] for p in dpath]

    await publish_session_event(
        guest_session_id,
        {
            "event": "PATH_UPDATE",
            "data": {
                "incident_id":   incident_id,
                "path_update":   new_path,
                "danger_path":   danger_path,
                "blocked_nodes": all_blocked,
            },
        },
    )
    return {"path_length": len(new_path), "new_path": new_path}