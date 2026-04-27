"""
app/vision/context_filter.py
─────────────────────────────
Filters YOLO detections to suppress expected events (armed guards on duty)
and focus on genuine threats before passing to the LLM classifier.
"""

from datetime import datetime
from app.vision.schemas import FrameDetection, VisionClassification, BoundingBox
from app.vision.pipeline_state import VisionPipelineState
from app.db.collections import get_cameras_on_floor
from app.db.firebase import get_db
import asyncio


def _iou(a: BoundingBox, b: dict) -> float:
    """Intersection-over-Union between a YOLO box and a guard-post bbox zone."""
    ax1, ay1, ax2, ay2 = a.x1, a.y1, a.x2, a.y2

    # Guard post bbox is expressed as fractions {x, y, w, h}
    frame_w, frame_h = 1.0, 1.0   # normalized
    bx1 = b["x"] * frame_w
    by1 = b["y"] * frame_h
    bx2 = bx1 + b["w"] * frame_w
    by2 = by1 + b["h"] * frame_h

    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter
    return inter / union if union > 0 else 0.0


async def _get_active_guard_posts(camera_id: str) -> list[dict]:
    """Load guard post suppression zones for this camera from Firestore."""
    db = get_db()
    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, lambda: list(
        db.collection("guard_posts")
        .where("camera_id", "==", camera_id)
        .where("active", "==", True)
        .stream()
    ))
    now_time = datetime.utcnow().time()
    result = []
    for d in docs:
        data = d.to_dict()
        # Only include if currently within shift
        try:
            start = datetime.strptime(data["shift_start"], "%H:%M").time()
            end   = datetime.strptime(data["shift_end"],   "%H:%M").time()
            if start <= now_time <= end and data.get("weapon_expected"):
                result.append(data)
        except Exception:
            pass
    return result


async def context_filter_node(state: VisionPipelineState) -> VisionPipelineState:
    """
    Examines each bounding box against registered guard posts.
    Suppresses 'person' + 'weapon' detections that overlap with guard positions.
    Remaining boxes are passed to the LLM threat classifier.
    """
    detection = state.raw_detection
    if not detection:
        state.error = "No detection payload"
        return state

    guard_posts = await _get_active_guard_posts(detection.camera_id)
    filtered_boxes: list[BoundingBox] = []
    suppressed = False
    suppression_reason = None

    for box in detection.boxes:
        if box.class_name in ("person", "weapon", "knife", "gun") and guard_posts:
            overlaps = [gp for gp in guard_posts if _iou(box, gp.get("bbox_zone", {})) > 0.4]
            if overlaps:
                suppressed = True
                suppression_reason = "guard_post"
                # Write suppression log (fire-and-forget)
                asyncio.create_task(_log_suppression(detection.camera_id, overlaps[0]["id"], box))
                continue   # skip this box
        filtered_boxes.append(box)

    # Rebuild detection with filtered boxes
    state.raw_detection = FrameDetection(
        camera_id    = detection.camera_id,
        frame_ts     = detection.frame_ts,
        boxes        = filtered_boxes,
        frame_width  = detection.frame_width,
        frame_height = detection.frame_height,
    )
    state.is_threat = len(filtered_boxes) > 0
    return state


async def _log_suppression(camera_id: str, post_id: str, box: BoundingBox):
    from datetime import datetime
    from app.db.collections import _id
    db = get_db()
    doc_id = _id()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: db.collection("suppression_logs").document(doc_id).set({
        "id":                   doc_id,
        "camera_id":            camera_id,
        "matched_post_id":      post_id,
        "detection_class":      box.class_name,
        "confidence":           box.confidence,
        "bbox":                 {"x1": box.x1, "y1": box.y1, "x2": box.x2, "y2": box.y2},
        "suppression_reason":   "guard_post",
        "was_inside_bbox_zone": True,
        "timestamp":            datetime.utcnow().isoformat(),
    }))
