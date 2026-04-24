import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, ForeignKey, Text, Time, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════
# GROUP 1 — ARCHITECTURE / DIGITAL TWIN
# ═══════════════════════════════════════════════════

class Hotel(Base):
    """Root venue. Every other table FK's here via hotel_id / venue_id."""
    __tablename__ = "hotels"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name        = Column(String(255), nullable=False)
    address     = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)

    blocks      = relationship("Block", back_populates="hotel")


class Block(Base):
    """Wing / block (A, B, C). Groups floors together spatially."""
    __tablename__ = "blocks"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hotel_id    = Column(UUID(as_uuid=False), ForeignKey("hotels.id"), nullable=False)
    name        = Column(String(100))           # e.g. "North Wing"
    block_code  = Column(String(10), nullable=False)  # "A", "B", "C"

    hotel       = relationship("Hotel", back_populates="blocks")
    floors      = relationship("Floor", back_populates="block")
    cameras     = relationship("Camera", back_populates="block")
    staff       = relationship("Staff", back_populates="block")


class Floor(Base):
    """
    One floor inside one block.
    static_grid is a JSONB 2D matrix: 0=walkable, 1=wall.
    A* pathfinding runs on this matrix at incident time.
    """
    __tablename__ = "floors"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    block_id    = Column(UUID(as_uuid=False), ForeignKey("blocks.id"), nullable=False)
    level       = Column(Integer, nullable=False)   # 1, 2, 3 ...
    grid_width  = Column(Integer, nullable=False)
    grid_height = Column(Integer, nullable=False)
    static_grid = Column(JSON, nullable=False)      # [[0,1,0,...], ...]

    block       = relationship("Block", back_populates="floors")
    pois        = relationship("POI", back_populates="floor")
    cameras     = relationship("Camera", back_populates="floor")
    incidents   = relationship("Incident", back_populates="floor")
    alerts      = relationship("EmergencyAlert", back_populates="floor")


class POI(Base):
    """
    Point of Interest — rooms, exits, stairwells, aid kits.
    coord_x / coord_y are grid positions inside the floor's static_grid.
    is_safe_exit=True → A* targets this POI as evacuation destination.
    """
    __tablename__ = "pois"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    floor_id    = Column(UUID(as_uuid=False), ForeignKey("floors.id"), nullable=False)
    name        = Column(String(100), nullable=False)   # "Room 204", "Stairwell B"
    type        = Column(String(30), nullable=False)    # room|exit|stairwell|utility|medical
    coord_x     = Column(Integer, nullable=False)
    coord_y     = Column(Integer, nullable=False)
    is_safe_exit = Column(Boolean, default=False)

    floor       = relationship("Floor", back_populates="pois")
    guests      = relationship("Guest", back_populates="room_poi")
    incidents   = relationship("Incident", back_populates="origin_poi")


# ═══════════════════════════════════════════════════
# GROUP 2 — SURVEILLANCE / VISION
# ═══════════════════════════════════════════════════

class Camera(Base):
    """Physical camera. coord_x/y = grid position on the floor."""
    __tablename__ = "cameras"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    block_id    = Column(UUID(as_uuid=False), ForeignKey("blocks.id"), nullable=False)
    floor_id    = Column(UUID(as_uuid=False), ForeignKey("floors.id"), nullable=False)
    coord_x     = Column(Integer)
    coord_y     = Column(Integer)
    stream_url  = Column(Text)
    active      = Column(Boolean, default=True)

    block           = relationship("Block", back_populates="cameras")
    floor           = relationship("Floor", back_populates="cameras")
    coverage_zones  = relationship("CameraCoverageZone", back_populates="camera")
    guard_posts     = relationship("GuardPost", back_populates="camera")
    suppression_logs = relationship("SuppressionLog", back_populates="camera")
    incidents       = relationship("Incident", back_populates="camera")


class CameraCoverageZone(Base):
    """
    Rectangular grid region a camera monitors.
    zone_name is injected into LLM prompts for human-readable location messages.
    Vision zone resolver uses start_x/y → end_x/y to find nearest POI.
    """
    __tablename__ = "camera_coverage_zones"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    camera_id   = Column(UUID(as_uuid=False), ForeignKey("cameras.id"), nullable=False)
    zone_name   = Column(String(100))       # "Lobby East", "Laundry Hallway"
    start_x     = Column(Integer, nullable=False)
    start_y     = Column(Integer, nullable=False)
    end_x       = Column(Integer, nullable=False)
    end_y       = Column(Integer, nullable=False)

    camera      = relationship("Camera", back_populates="coverage_zones")


class GuardPost(Base):
    """
    Registered armed guard positions. Context filter uses this to
    suppress YOLO weapon detections that are expected (guard on duty).
    """
    __tablename__ = "guard_posts"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    camera_id       = Column(UUID(as_uuid=False), ForeignKey("cameras.id"), nullable=False)
    staff_id        = Column(UUID(as_uuid=False), ForeignKey("staff.id"), nullable=True)
    bbox_zone       = Column(JSON)              # {x,y,w,h} as fraction of frame
    shift_start     = Column(Time)
    shift_end       = Column(Time)
    weapon_expected = Column(Boolean, default=True)
    uniform_color   = Column(String(50))
    active          = Column(Boolean, default=True)

    camera          = relationship("Camera", back_populates="guard_posts")
    staff           = relationship("Staff", back_populates="guard_posts")
    suppression_logs = relationship("SuppressionLog", back_populates="guard_post")


class SuppressionLog(Base):
    """Audit trail of every YOLO detection that was suppressed. Never silent."""
    __tablename__ = "suppression_logs"

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    camera_id           = Column(UUID(as_uuid=False), ForeignKey("cameras.id"), nullable=False)
    matched_post_id     = Column(UUID(as_uuid=False), ForeignKey("guard_posts.id"), nullable=True)
    detection_class     = Column(String(50))    # weapon | person etc.
    confidence          = Column(Float)
    bbox                = Column(JSON)
    suppression_reason  = Column(String(50))    # guard_post|shift_hours|bbox_zone
    was_inside_bbox_zone = Column(Boolean)
    timestamp           = Column(DateTime, default=datetime.utcnow)

    camera      = relationship("Camera", back_populates="suppression_logs")
    guard_post  = relationship("GuardPost", back_populates="suppression_logs")


# ═══════════════════════════════════════════════════
# GROUP 3 — OCCUPANTS / PEOPLE
# ═══════════════════════════════════════════════════

class Staff(Base):
    """Hotel responders. current_floor/block updated via heartbeat PATCH."""
    __tablename__ = "staff"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hotel_id        = Column(UUID(as_uuid=False), ForeignKey("hotels.id"), nullable=False)
    name            = Column(String(255), nullable=False)
    role            = Column(String(50))        # security|medical|manager|front_desk
    phone           = Column(String(30))
    current_floor_id = Column(UUID(as_uuid=False), ForeignKey("floors.id"), nullable=True)
    current_block_id = Column(UUID(as_uuid=False), ForeignKey("blocks.id"), nullable=True)
    current_status  = Column(String(30), default="available")  # available|on_incident|off_duty
    on_duty         = Column(Boolean, default=False)

    block           = relationship("Block", back_populates="staff")
    guard_posts     = relationship("GuardPost", back_populates="staff")
    assignments     = relationship("StaffAssignment", back_populates="staff")
    dispatches      = relationship("Dispatch", back_populates="staff")


class Guest(Base):
    """
    Active hotel guest.
    poi_id → pois table → coord_x/y + floor_id → block_id.
    This chain is how the enricher resolves physical location.
    """
    __tablename__ = "guests"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hotel_id    = Column(UUID(as_uuid=False), ForeignKey("hotels.id"), nullable=False)
    poi_id      = Column(UUID(as_uuid=False), ForeignKey("pois.id"), nullable=True)  # their room
    name        = Column(String(255))
    phone       = Column(String(30))
    language    = Column(String(10), default="en")
    session_id  = Column(String(100))               # current WebSocket session
    check_in    = Column(DateTime)
    check_out   = Column(DateTime)

    room_poi    = relationship("POI", back_populates="guests")
    chat_sessions = relationship("ChatSession", back_populates="guest")


class StaffAssignment(Base):
    """Static sector responsibility — which block/floor a staff member covers."""
    __tablename__ = "staff_assignments"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    staff_id    = Column(UUID(as_uuid=False), ForeignKey("staff.id"), nullable=False)
    block_id    = Column(UUID(as_uuid=False), ForeignKey("blocks.id"), nullable=False)
    floor_id    = Column(UUID(as_uuid=False), ForeignKey("floors.id"), nullable=True)

    staff       = relationship("Staff", back_populates="assignments")


# ═══════════════════════════════════════════════════
# GROUP 4 — CRISIS RESPONSE / EVENT LAYER
# ═══════════════════════════════════════════════════

class Incident(Base):
    """
    Core event record. source = 'chat' | 'vision'.
    origin_poi = the POI where the threat was detected.
    camera_id set if source=vision, null if source=chat.
    message_id set if source=chat, null if source=vision.
    """
    __tablename__ = "incidents"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hotel_id    = Column(UUID(as_uuid=False), ForeignKey("hotels.id"), nullable=False)
    floor_id    = Column(UUID(as_uuid=False), ForeignKey("floors.id"), nullable=True)
    camera_id   = Column(UUID(as_uuid=False), ForeignKey("cameras.id"), nullable=True)
    message_id  = Column(UUID(as_uuid=False), ForeignKey("chat_messages.id"), nullable=True)
    origin_poi_id = Column(UUID(as_uuid=False), ForeignKey("pois.id"), nullable=True)
    type        = Column(String(50), nullable=False)    # fire|medical|security|crowd
    severity    = Column(Integer, nullable=False)       # 1-5
    status      = Column(String(30), default="active") # active|resolved|false_alarm
    source      = Column(String(10), nullable=False)    # chat|vision
    full_location = Column(Text)
    blocked_nodes = Column(JSON)    # [[x,y],...] — hazard cells on the grid
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    floor       = relationship("Floor", back_populates="incidents")
    camera      = relationship("Camera", back_populates="incidents")
    origin_poi  = relationship("POI", back_populates="incidents")
    chat_message = relationship("ChatMessage", back_populates="incident", uselist=False)
    alerts      = relationship("EmergencyAlert", back_populates="incident")
    dispatches  = relationship("Dispatch", back_populates="incident")


class EmergencyAlert(Base):
    """
    Dynamic hazard overlay for a floor's grid.
    blocked_nodes are sent to frontend via THREAT_DETECTED WebSocket event.
    Frontend colors these cells red. Backend re-runs A* around them.
    """
    __tablename__ = "emergency_alerts"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    incident_id     = Column(UUID(as_uuid=False), ForeignKey("incidents.id"), nullable=False)
    floor_id        = Column(UUID(as_uuid=False), ForeignKey("floors.id"), nullable=False)
    blocked_nodes   = Column(JSON, nullable=False)  # [[x,y], ...]
    radius          = Column(Float)                 # grid units of hazard spread
    created_at      = Column(DateTime, default=datetime.utcnow)

    incident    = relationship("Incident", back_populates="alerts")
    floor       = relationship("Floor", back_populates="alerts")


class Dispatch(Base):
    """
    Real-time tracking of staff response to an incident.
    ack_watchdog queries ack_status=PENDING rows older than 60s to re-alert.
    """
    __tablename__ = "dispatches"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    incident_id = Column(UUID(as_uuid=False), ForeignKey("incidents.id"), nullable=False)
    staff_id    = Column(UUID(as_uuid=False), ForeignKey("staff.id"), nullable=False)
    message_text = Column(Text)
    ack_status  = Column(String(20), default="PENDING")  # PENDING|ACCEPTED|ON_SCENE
    sent_at     = Column(DateTime, default=datetime.utcnow)
    acked_at    = Column(DateTime, nullable=True)

    incident    = relationship("Incident", back_populates="dispatches")
    staff       = relationship("Staff", back_populates="dispatches")


# ═══════════════════════════════════════════════════
# GROUP 5 — CHAT PIPELINE / MESSAGE LAYER
# ═══════════════════════════════════════════════════

class ChatSession(Base):
    """One WebSocket session per guest connection."""
    __tablename__ = "chat_sessions"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hotel_id    = Column(UUID(as_uuid=False), ForeignKey("hotels.id"), nullable=False)
    guest_id    = Column(UUID(as_uuid=False), ForeignKey("guests.id"), nullable=True)
    poi_id      = Column(UUID(as_uuid=False), ForeignKey("pois.id"), nullable=True)
    sender_type = Column(String(20), nullable=False)    # guest|staff|anonymous
    started_at  = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    guest       = relationship("Guest", back_populates="chat_sessions")
    messages    = relationship("ChatMessage", back_populates="session")



class ChatMessage(Base):
    """
    Every message persisted with NLP output baked in.
    threat_type + severity + confidence written by nlp_classifier node.
    """
    __tablename__ = "chat_messages"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id      = Column(UUID(as_uuid=False), ForeignKey("chat_sessions.id"), nullable=False)
    raw_text        = Column(Text, nullable=False)
    language        = Column(String(10), default="en")
    threat_type     = Column(String(50))    # medical|fire|security|crowd|none
    severity        = Column(String(20))    # CRITICAL|HIGH|MEDIUM|LOW|NONE
    nlp_confidence  = Column(Float)
    victim_entity   = Column(String(100))
    symptom_entity  = Column(String(100))
    sent_at         = Column(DateTime, default=datetime.utcnow)

    session     = relationship("ChatSession", back_populates="messages")
    incident    = relationship("Incident", back_populates="chat_message", uselist=False)