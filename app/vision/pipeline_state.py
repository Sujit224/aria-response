"""
app/vision/pipeline_state.py
────────────────────────────
LangGraph state definition for the vision pipeline.
Flows: FrameDetection → context_filter → threat_classifier → zone_resolver → alert_dispatcher
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field
from app.vision.schemas import (
    FrameDetection, VisionClassification,
    VisionZoneResolution, VisionAlertPayload,
)


class VisionPipelineState(BaseModel):
    """
    Mutable state that flows through the YOLO vision LangGraph pipeline.
    Each node fills its own field and passes the state to the next.
    """
    raw_detection:  Optional[FrameDetection]       = None
    classification: Optional[VisionClassification] = None
    zone:           Optional[VisionZoneResolution] = None
    alert:          Optional[VisionAlertPayload]   = None
    error:          Optional[str]                  = None
    is_threat:      bool                           = False
    venue_id:       str                            = ""
