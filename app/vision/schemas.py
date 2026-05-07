"""
app/vision/schemas.py
─────────────────────
Pydantic models for the vision pipeline.
Mirrors the LangGraph state shape for camera events.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str


class FrameDetection(BaseModel):
    """Raw YOLO output for a single frame."""
    camera_id:   str
    frame_ts:    str           # ISO datetime of capture
    boxes:       List[BoundingBox]
    frame_width: int
    frame_height: int


class VisionClassification(BaseModel):
    """Result after context filter + LLM threat classifier."""
    camera_id:       str
    threat_type:     str       # fire | medical | security | crowd | none
    confidence:      float
    severity:        str       # CRITICAL | HIGH | MEDIUM | LOW | NONE
    is_threat:       bool
    description:     str       # human-readable LLM summary
    suppressed:      bool      # True if guard-post suppression was applied
    suppression_reason: Optional[str]
    zone_name:       Optional[str]   # from CameraCoverageZone
    boxes:           List[BoundingBox]
    frame_ts:        str


class VisionZoneResolution(BaseModel):
    """Zone + path info enriched from the camera's coverage zone."""
    incident_id:       str
    camera_id:         str
    floor_id:          str
    threat_type:       str
    severity:          str
    full_location:     str
    blocked_nodes:     List[List[int]]
    nearest_exit_name: str
    path_to_exit:      List[List[int]]
    staff_on_floor:    List[str]


class VisionAlertPayload(BaseModel):
    """Final payload published to Firestore channels."""
    event:         str = "THREAT_DETECTED"
    incident_id:   str
    camera_id:     str
    type:          str
    severity:      str
    full_location: str
    zone_name:     str
    blocked_nodes: List[List[int]]
    path_update:   List[List[int]]
    description:   str
