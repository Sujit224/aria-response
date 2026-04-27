"""
app/api/occupants.py
────────────────────
Room occupant management — the new front-desk API.

POST   /api/v1/occupants/checkin              Register guest to a room (stores phone + FCM token)
DELETE /api/v1/occupants/{room_id}/{phone}     Check out a guest from a room
PATCH  /api/v1/occupants/{room_id}/fcm_token  Update FCM token after PWA permission grant
GET    /api/v1/occupants/{hotel_id}/{floor_id} List all occupied rooms on a floor
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.collections import (
    save_room_occupant,
    remove_room_occupant,
    update_fcm_token,
    get_room_occupants_on_floor,
    get_poi_chain,
)

router = APIRouter(prefix="/occupants", tags=["occupants"])


class CheckInRequest(BaseModel):
    hotel_id:   str
    room_id:    str     # POI id of the room
    name:       str
    phone:      str
    language:   str = "en"
    fcm_token:  str | None = None


class FCMTokenUpdate(BaseModel):
    phone:     str
    fcm_token: str


@router.post("/checkin")
async def checkin(body: CheckInRequest):
    """
    Front desk registers a guest to a room.
    Resolves room metadata (coords, floor, block) from the POI chain.

    The guest's FCM token can be provided at check-in time (if the device is
    already registered) or later via PATCH /fcm_token when the PWA requests
    notification permission.
    """
    chain = await get_poi_chain(body.room_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Room POI not found")

    await save_room_occupant(
        room_id     = body.room_id,
        hotel_id    = body.hotel_id,
        floor_id    = chain["floor_id"],
        block_id    = chain["block_id"],
        room_name   = chain["name"],
        room_number = chain["name"].replace("Room ", ""),
        block_code  = chain["block_code"],
        floor_level = chain["floor_level"],
        coord_x     = chain["coord_x"],
        coord_y     = chain["coord_y"],
        name        = body.name,
        phone       = body.phone,
        fcm_token   = body.fcm_token,
        language    = body.language,
    )
    return {
        "status":     "checked_in",
        "room":       chain["name"],
        "floor":      chain["floor_level"],
        "block":      chain["block_code"],
    }


@router.delete("/{room_id}/{phone}")
async def checkout(room_id: str, phone: str):
    """Front desk checks a guest out of a room."""
    await remove_room_occupant(room_id, phone)
    return {"status": "checked_out", "room_id": room_id, "phone": phone}


@router.patch("/{room_id}/fcm_token")
async def register_fcm_token(room_id: str, body: FCMTokenUpdate):
    """
    Called by the Guest PWA after the user grants notification permission.
    Associates their FCM device token with their room so they receive
    personalised evacuation push notifications during an emergency.
    """
    await update_fcm_token(room_id, body.phone, body.fcm_token)
    return {"status": "token_registered", "room_id": room_id}


@router.get("/{hotel_id}/{floor_id}")
async def list_occupants(hotel_id: str, floor_id: str):
    """
    Returns all occupied rooms on a floor with guest names and phone numbers.
    Staff dashboard uses this to see who is currently checked in per floor.
    FCM tokens are omitted from this response for privacy.
    """
    rooms = await get_room_occupants_on_floor(floor_id)
    # Filter by hotel and strip FCM tokens
    result = []
    for room in rooms:
        if room.get("hotel_id") != hotel_id:
            continue
        occupants_safe = [
            {"name": o["name"], "phone": o["phone"], "language": o["language"],
             "checked_in_at": o.get("checked_in_at")}
            for o in room.get("occupants", [])
        ]
        result.append({
            "room_id":    room["room_id"],
            "room_name":  room["room_name"],
            "floor_level": room["floor_level"],
            "block_code": room["block_code"],
            "coord_x":    room["coord_x"],
            "coord_y":    room["coord_y"],
            "occupants":  occupants_safe,
        })
    return result
