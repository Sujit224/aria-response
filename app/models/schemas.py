from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime
import uuid


# ─────────────────────────────────────────
# INBOUND
# ─────────────────────────────────────────

class IncomingMessage(BaseModel):
    session_id: Optional[str] = None   # None = new session
    raw_text: str
    room_id: Optional[str] = None      # poi_id of the guest's room
    venue_id: str                       # hotel_id
    language: str = "en"


# ─────────────────────────────────────────
# ENRICHED
# ─────────────────────────────────────────

class EnrichedMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    venue_id: str
    raw_text: str
    language: str
    poi_id: Optional[str] = None
    room_number: Optional[str] = None
    floor_id: Optional[str] = None
    floor_level: Optional[int] = None
    block_id: Optional[str] = None
    block_code: Optional[str] = None
    wing: Optional[str] = None
    coord_x: Optional[int] = None
    coord_y: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────
# NLP RESULT
# ─────────────────────────────────────────

class NLPResult(BaseModel):
    message_id: str
    session_id: str
    threat_type: str        # medical | fire | security | crowd | none
    confidence: float
    severity: str           # CRITICAL | HIGH | MEDIUM | LOW | NONE
    is_threat: bool
    victim_entity: Optional[str] = None
    symptom_entity: Optional[str] = None
    poi_id: Optional[str] = None
    room_number: Optional[str] = None
    floor_id: Optional[str] = None
    floor_level: Optional[int] = None
    block_id: Optional[str] = None
    block_code: Optional[str] = None
    coord_x: Optional[int] = None
    coord_y: Optional[int] = None
    venue_id: str
    raw_text: str


# ─────────────────────────────────────────
# ZONE RESOLUTION
# ─────────────────────────────────────────

class Coord(BaseModel):
    x: int
    y: int

class ZoneResolution(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    threat_type: str
    severity: str
    source: str                         # "chat" | "vision"
    room_number: str
    block_code: str
    floor_level: int
    wing: Optional[str] = None
    full_location: str
    zone_1_rooms: List[str]
    zone_2_rooms: List[str]
    zone_3_rooms: List[str]
    nearest_exit_name: str
    nearest_exit_coord: Coord
    nearest_aid_kit: str
    evacuation_path: List[Coord]        # A* result
    blocked_nodes: List[Coord]          # hazard overlay for frontend
    staff_on_floor: List[str]
    session_id: str
    venue_id: str
    message_id: str


# ─────────────────────────────────────────
# GENERATED MESSAGES
# ─────────────────────────────────────────

class GeneratedMessages(BaseModel):
    incident_id: str
    severity: str
    msg_guest_ack: str
    msg_staff_zone1: str
    msg_staff_zone2: str
    msg_staff_zone3: str
    msg_responder: str
    dashboard_summary: str
    suggested_actions: List[str]
    session_id: str
    venue_id: str


# ─────────────────────────────────────────
# PIPELINE STATE
# ─────────────────────────────────────────

class PipelineState(BaseModel):
    incoming: Optional[IncomingMessage] = None
    enriched: Optional[EnrichedMessage] = None
    nlp: Optional[NLPResult] = None
    zone: Optional[ZoneResolution] = None
    messages: Optional[GeneratedMessages] = None
    error: Optional[str] = None
    is_threat: bool = False


# ─────────────────────────────────────────
# WEBSOCKET OUTBOUND SHAPES
# ─────────────────────────────────────────

class WSOutbound(BaseModel):
    type: Literal[
        "THREAT_DETECTED", "STAFF_DISPATCHED", "INCIDENT_RESOLVED",
        "CHAT_ACK", "PATH_UPDATE", "normal_reply", "error",
    ]
    session_id: str
    payload: dict


class ThreatDetectedPayload(BaseModel):
    incident_id: str
    type: str
    severity: str
    zone_name: str
    full_location: str
    blocked_nodes: List[List[int]]      # [[x,y], ...]
    path_update: List[List[int]]        # [[x,y], ...] A* green path


class StaffDispatchedPayload(BaseModel):
    staff_name: str
    eta_minutes: int
    status: str                         # DISPATCHED | ARRIVING_NOW | ON_SCENE


# ─────────────────────────────────────────
# ADMIN INGESTION REQUEST BODIES
# ─────────────────────────────────────────

class CreateHotelRequest(BaseModel):
    name: str
    address: str

class CreateBlockRequest(BaseModel):
    hotel_id: str
    name: str
    block_code: str

class FloorGridRequest(BaseModel):
    block_id: str
    level: int
    grid_width: int
    grid_height: int
    static_grid: List[List[int]]        # 0=walkable, 1=wall

class POIRequest(BaseModel):
    floor_id: str
    name: str
    type: str                           # room|exit|stairwell|utility|medical
    coord_x: int
    coord_y: int
    is_safe_exit: bool = False

class CoverageZoneRequest(BaseModel):
    zone_name: str
    start_x: int
    start_y: int
    end_x: int
    end_y: int

class CreateCameraRequest(BaseModel):
    block_id: str
    floor_id: str
    coord_x: int
    coord_y: int
    stream_url: str
    coverage_zones: List[CoverageZoneRequest] = []