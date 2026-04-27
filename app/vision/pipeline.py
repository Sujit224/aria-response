"""
app/vision/pipeline.py
───────────────────────
LangGraph pipeline for vision (YOLO camera) events.

Flow:
  raw YOLO detection
    → context_filter   (suppress guard posts)
    → threat_classifier (Claude / rule-based)
    → [is_threat?]
      YES: zone_resolver → llm_responder → alert_dispatcher
      NO:  END
"""

from langgraph.graph import StateGraph, END
from app.vision.pipeline_state import VisionPipelineState
from app.vision.context_filter import context_filter_node
from app.vision.threat_classifier import threat_classifier_node
from app.vision.zone_resolver import vision_zone_resolver_node
from app.vision.llm_responder import vision_llm_responder_node
from app.vision.alert_dispatcher import vision_alert_dispatcher_node


def _route_threat(state: VisionPipelineState) -> str:
    return "zone_resolver" if state.is_threat else END


def build_vision_pipeline():
    g = StateGraph(VisionPipelineState)

    g.add_node("context_filter",   context_filter_node)
    g.add_node("classifier",       threat_classifier_node)
    g.add_node("zone_resolver",    vision_zone_resolver_node)
    g.add_node("llm_responder",    vision_llm_responder_node)
    g.add_node("alert_dispatcher", vision_alert_dispatcher_node)

    g.set_entry_point("context_filter")
    g.add_edge("context_filter", "classifier")
    g.add_conditional_edges("classifier", _route_threat, {
        "zone_resolver": "zone_resolver",
        END: END,
    })
    g.add_edge("zone_resolver",    "llm_responder")
    g.add_edge("llm_responder",    "alert_dispatcher")
    g.add_edge("alert_dispatcher", END)

    return g.compile()


vision_pipeline = build_vision_pipeline()
