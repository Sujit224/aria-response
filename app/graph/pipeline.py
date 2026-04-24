from langgraph.graph import StateGraph, END
from app.models.schemas import PipelineState
from app.graph.nodes.enricher import enricher_node
from app.graph.nodes.nlp_classifier import nlp_classifier_node
from app.graph.nodes.zone_resolver import zone_resolver_node
from app.graph.nodes.llm_responder import llm_responder_node
from app.graph.nodes.alert_dispatcher import alert_dispatcher_node, normal_reply_node


def route_after_nlp(state: PipelineState) -> str:
    """Conditional edge: threat → full pipeline, normal → friendly reply only."""
    if state.is_threat and not state.error:
        return "zone_resolver"
    return "normal_reply"


def route_after_zone(state: PipelineState) -> str:
    """If zone resolution failed (missing room data), bail out gracefully."""
    if state.error:
        return END
    return "llm_responder"


def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("enricher", enricher_node)
    graph.add_node("nlp_classifier", nlp_classifier_node)
    graph.add_node("zone_resolver", zone_resolver_node)
    graph.add_node("llm_responder", llm_responder_node)
    graph.add_node("alert_dispatcher", alert_dispatcher_node)
    graph.add_node("normal_reply", normal_reply_node)

    graph.set_entry_point("enricher")

    graph.add_edge("enricher", "nlp_classifier")

    graph.add_conditional_edges(
        "nlp_classifier",
        route_after_nlp,
        {
            "zone_resolver": "zone_resolver",
            "normal_reply": "normal_reply",
        },
    )

    graph.add_conditional_edges(
        "zone_resolver",
        route_after_zone,
        {
            "llm_responder": "llm_responder",
            END: END,
        },
    )

    graph.add_edge("llm_responder", "alert_dispatcher")
    graph.add_edge("alert_dispatcher", END)
    graph.add_edge("normal_reply", END)

    return graph.compile()


# Singleton compiled pipeline
aria_pipeline = build_pipeline()