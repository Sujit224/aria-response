"""
app/vision/threat_classifier.py
────────────────────────────────
Uses Claude to classify filtered YOLO bounding boxes into threat categories.
Falls back to a deterministic rule-based classifier if LLM call fails.
"""

import os, json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.vision.pipeline_state import VisionPipelineState
from app.vision.schemas import VisionClassification

llm = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

SYSTEM_PROMPT = """You are a security camera threat classification AI.
Given a list of YOLO object detections, return ONLY a JSON object:
{
  "threat_type": one of ["fire", "medical", "security", "crowd", "none"],
  "severity":    one of ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"],
  "confidence":  float 0.0-1.0,
  "is_threat":   true | false,
  "description": "one sentence summary of what was detected"
}
Rules:
- fire / smoke detection → fire CRITICAL
- person collapsed / not moving → medical HIGH
- weapon / knife / gun visible → security CRITICAL
- crowd density >10 people in frame → crowd MEDIUM
- person walking normally → none
- Return ONLY the JSON object."""

# Deterministic fallback rules (class_name → threat)
_RULE_MAP = {
    "fire":   ("fire",     "CRITICAL", 0.92),
    "smoke":  ("fire",     "HIGH",     0.80),
    "knife":  ("security", "CRITICAL", 0.95),
    "gun":    ("security", "CRITICAL", 0.97),
    "weapon": ("security", "CRITICAL", 0.90),
}


def _rule_based(boxes) -> dict:
    for box in boxes:
        if box.class_name in _RULE_MAP:
            th, sev, conf = _RULE_MAP[box.class_name]
            return {
                "threat_type": th, "severity": sev,
                "confidence": conf, "is_threat": True,
                "description": f"Detected {box.class_name} with confidence {box.confidence:.0%}",
            }
    return {"threat_type": "none", "severity": "NONE", "confidence": 0.0,
            "is_threat": False, "description": "No threat detected"}


async def threat_classifier_node(state: VisionPipelineState) -> VisionPipelineState:
    detection = state.raw_detection
    if not detection or not detection.boxes:
        state.is_threat = False
        return state

    boxes_summary = [
        {"class": b.class_name, "confidence": round(b.confidence, 2)} for b in detection.boxes
    ]

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Detected objects: {json.dumps(boxes_summary)}"),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except Exception:
        parsed = _rule_based(detection.boxes)

    # Get zone name from coverage zone DB (best-effort)
    zone_name = None

    state.classification = VisionClassification(
        camera_id          = detection.camera_id,
        threat_type        = parsed.get("threat_type", "none"),
        confidence         = parsed.get("confidence", 0.0),
        severity           = parsed.get("severity", "NONE"),
        is_threat          = parsed.get("is_threat", False),
        description        = parsed.get("description", ""),
        suppressed         = False,
        suppression_reason = None,
        zone_name          = zone_name,
        boxes              = detection.boxes,
        frame_ts           = detection.frame_ts,
    )
    state.is_threat = state.classification.is_threat
    return state
