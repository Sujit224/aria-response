"""
app/models/tables.py
────────────────────
Firestore Document Schemas — ARIA v2.0 (Firebase)

This file defines TypedDict schemas for every Firestore collection.
These are used for type-checking and IDE autocomplete across the codebase.

There are NO SQLAlchemy models or Alembic migrations in this version.
All collections are managed implicitly by Firestore (schema-less).

Collection Map
──────────────
hotels/{hotel_id}
blocks/{block_id}
floors/{floor_id}
pois/{poi_id}
cameras/{camera_id}
  └─ coverage_zones/{zone_id}      subcollection
guard_posts/{post_id}
suppression_logs/{log_id}
staff/{staff_id}
room_occupants/{room_id}           ← stores room number + guest phone numbers
  └─ occupants[]                   ← embedded array of current guests
guests/{guest_id}
chat_sessions/{session_id}
  └─ events/{event_id}             ← real-time event stream (replaces Redis)
chat_messages/{message_id}
incidents/{incident_id}
emergency_alerts/{alert_id}
dispatches/{dispatch_id}
venues/{venue_id}
  └─ staff_events/{event_id}       ← staff broadcast channel
  └─ dashboard_events/{event_id}   ← dashboard broadcast channel
"""

from typing import Optional, List
from typing_extensions import TypedDict


# ═══════════════════════════════════════════════════════════════════
# GROUP 1 — ARCHITECTURE / DIGITAL TWIN
# ═══════════════════════════════════════════════════════════════════

class HotelDoc(TypedDict):
    id:         str
    name:       str
    address:    str
    created_at: str                 # ISO datetime string


class BlockDoc(TypedDict):
    id:         str
    hotel_id:   str
    name:       str                 # "North Wing"
    block_code: str                 # "A", "B", "C"


class FloorDoc(TypedDict):
    id:          str
    block_id:    str
    level:       int                # 1, 2, 3 ...
    grid_width:  int
    grid_height: int
    static_grid: List[List[int]]    # 2D matrix: 0=walkable, 1=wall


class POIDoc(TypedDict):
    id:           str
    floor_id:     str
    name:         str               # "Room 204", "Stairwell B", "Exit A"
    type:         str               # room | exit | stairwell | utility | medical
    coord_x:      int               # grid column position
    coord_y:      int               # grid row position
    is_safe_exit: bool              # True → A* evacuation target


# ═══════════════════════════════════════════════════════════════════
# GROUP 2 — SURVEILLANCE / VISION
# ═══════════════════════════════════════════════════════════════════

class CoverageZoneDoc(TypedDict):
    id:        str
    camera_id: str
    zone_name: str                  # "Lobby East", "Corridor B"
    start_x:   int
    start_y:   int
    end_x:     int
    end_y:     int


class CameraDoc(TypedDict):
    id:              str
    block_id:        str
    floor_id:        str
    coord_x:         int
    coord_y:         int
    stream_url:      str            # rtsp://...
    active:          bool
    # coverage_zones is stored as a subcollection, not embedded


class GuardPostDoc(TypedDict):
    id:              str
    camera_id:       str
    staff_id:        Optional[str]
    bbox_zone:       dict           # {x, y, w, h} as fraction of frame
    shift_start:     str            # "08:00"
    shift_end:       str            # "20:00"
    weapon_expected: bool
    uniform_color:   str
    active:          bool


class SuppressionLogDoc(TypedDict):
    id:                   str
    camera_id:            str
    matched_post_id:      Optional[str]
    detection_class:      str       # weapon | person | ...
    confidence:           float
    bbox:                 dict      # {x1, y1, x2, y2}
    suppression_reason:   str       # guard_post | shift_hours | bbox_zone
    was_inside_bbox_zone: bool
    timestamp:            str       # ISO datetime


# ═══════════════════════════════════════════════════════════════════
# GROUP 3 — OCCUPANTS / PEOPLE
# ═══════════════════════════════════════════════════════════════════

class StaffDoc(TypedDict):
    id:               str
    hotel_id:         str
    name:             str
    role:             str           # security | medical | manager | front_desk
    phone:            str
    current_floor_id: Optional[str]
    current_block_id: Optional[str]
    current_status:   str           # available | on_incident | off_duty
    on_duty:          bool


class GuestDoc(TypedDict):
    id:         str
    hotel_id:   str
    poi_id:     Optional[str]       # room POI — used to resolve coords
    name:       str
    phone:      str
    language:   str                 # "en", "hi", "ar" ...
    session_id: str                 # current WebSocket session_id
    check_in:   str                 # ISO datetime
    check_out:  str                 # ISO datetime


class StaffAssignmentDoc(TypedDict):
    id:       str
    staff_id: str
    block_id: str
    floor_id: Optional[str]


# ──────────────────────────────────────────────────────────────────
# *** NEW *** room_occupants collection
# Stores room number + all currently checked-in guest phones and
# FCM tokens so ARIA can send personalised evacuation notifications.
# ──────────────────────────────────────────────────────────────────

class OccupantEntry(TypedDict):
    """One guest currently staying in the room."""
    name:           str             # Guest full name
    phone:          str             # Mobile number (used as unique key per room)
    fcm_token:      Optional[str]   # Firebase Cloud Messaging device token
                                    # Registered by Guest PWA after notif. permission
    language:       str             # Preferred language for notif. text
    checked_in_at:  str             # ISO datetime of check-in


class RoomOccupantsDoc(TypedDict):
    """
    Firestore Collection: room_occupants
    Document ID: poi_id of the room (same as POI.id)

    One document per room. The `occupants` array holds every guest
    currently checked into that room. Most rooms will have 1-2 guests.

    At incident time, fcm_notifier.py queries this collection for the
    affected floor and sends each occupant a personalised push notification
    containing their own A*-computed evacuation path and turn-by-turn steps.

    Front desk manages this via:
      POST   /api/v1/occupants/checkin
      DELETE /api/v1/occupants/{room_id}/{phone}
      PATCH  /api/v1/occupants/{room_id}/fcm_token
      GET    /api/v1/occupants/{hotel_id}/{floor_id}
    """
    room_id:     str            # POI id — links to pois/{room_id}
    hotel_id:    str
    floor_id:    str
    block_id:    str
    room_name:   str            # "Room 204"
    room_number: str            # "204"  (short form for display)
    block_code:  str            # "B"
    floor_level: int            # 2
    coord_x:     int            # grid column (used by A* path origin)
    coord_y:     int            # grid row    (used by A* path origin)
    occupants:   List[OccupantEntry]   # ← current guests in this room


# ═══════════════════════════════════════════════════════════════════
# GROUP 4 — CRISIS RESPONSE / EVENT LAYER
# ═══════════════════════════════════════════════════════════════════

class IncidentDoc(TypedDict):
    id:            str
    hotel_id:      str
    floor_id:      Optional[str]
    camera_id:     Optional[str]    # set if source=vision
    message_id:    Optional[str]    # set if source=chat
    origin_poi_id: Optional[str]    # room/area where threat originated
    type:          str              # fire | medical | security | crowd
    severity:      int              # 1 (low) – 5 (critical)
    status:        str              # active | resolved | false_alarm
    source:        str              # chat | vision
    full_location: str              # "Block B, Room 204, Floor 2"
    blocked_nodes: List[List[int]]  # [[x,y], ...] hazard grid cells
    detected_at:   str              # ISO datetime
    resolved_at:   Optional[str]    # ISO datetime


class EmergencyAlertDoc(TypedDict):
    id:            str
    incident_id:   str
    floor_id:      str
    blocked_nodes: List[List[int]]  # [[x,y], ...] — drawn red on floor map
    radius:        float            # grid-unit radius of hazard spread
    created_at:    str              # ISO datetime


class DispatchDoc(TypedDict):
    id:           str
    incident_id:  str
    staff_id:     str
    message_text: str
    ack_status:   str               # PENDING | ACCEPTED | ON_SCENE
    sent_at:      str               # ISO datetime
    acked_at:     Optional[str]     # ISO datetime


# ═══════════════════════════════════════════════════════════════════
# GROUP 5 — CHAT PIPELINE / MESSAGE LAYER
# ═══════════════════════════════════════════════════════════════════

class ChatSessionDoc(TypedDict):
    id:          str
    hotel_id:    str
    guest_id:    Optional[str]
    poi_id:      Optional[str]
    sender_type: str                # guest | staff | anonymous
    started_at:  str
    last_active: str


class ChatMessageDoc(TypedDict):
    id:             str
    session_id:     str
    raw_text:       str
    language:       str
    threat_type:    str             # medical | fire | security | crowd | none
    severity:       str             # CRITICAL | HIGH | MEDIUM | LOW | NONE
    nlp_confidence: float
    victim_entity:  Optional[str]
    symptom_entity: Optional[str]
    sent_at:        str             # ISO datetime


# ═══════════════════════════════════════════════════════════════════
# GROUP 6 — REAL-TIME EVENT DOCS (replaces Redis Pub/Sub)
# Subcollections appended by alert_dispatcher; read via on_snapshot
# ═══════════════════════════════════════════════════════════════════

class SessionEventDoc(TypedDict):
    """chat_sessions/{session_id}/events/{event_id}"""
    event: str                      # THREAT_DETECTED | CHAT_ACK | PATH_UPDATE | error
    data:  dict
    _ts:   str                      # server timestamp

class StaffEventDoc(TypedDict):
    """venues/{venue_id}/staff_events/{event_id}"""
    event: str                      # STAFF_ALERT | DISPATCH_REMINDER
    data:  dict
    _ts:   str

class DashboardEventDoc(TypedDict):
    """venues/{venue_id}/dashboard_events/{event_id}"""
    event: str                      # INCIDENT_UPDATE | INCIDENT_RESOLVED
    data:  dict
    _ts:   str