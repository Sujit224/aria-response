"""
app/vision/llm_responder.py
────────────────────────────
Generates role-specific alert messages for vision-triggered incidents.
Reuses the same Claude call pattern as the chat pipeline's llm_responder.
"""

import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.vision.pipeline_state import VisionPipelineState

llm = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)


async def vision_llm_responder_node(state: VisionPipelineState) -> VisionPipelineState:
    """
    Generates a brief staff alert message for vision-detected incidents.
    The output is embedded in the STAFF_ALERT Firestore event payload.
    For vision incidents there is no guest chat, so we generate staff-only messages.
    """
    clsf = state.classification
    zone = state.zone
    if not clsf or not zone:
        return state

    prompt = (
        f"A {clsf.severity} {clsf.threat_type} incident was detected by CCTV at {zone.full_location}.\n"
        f"Description: {clsf.description}\n"
        f"Write a brief 2-sentence alert for security staff. Be direct, professional, and clear."
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content="You write emergency alerts for hotel security staff. Be concise and professional."),
            HumanMessage(content=prompt),
        ])
        state.alert.description = response.content.strip()
    except Exception:
        state.alert.description = (
            f"[VISION] {clsf.severity} {clsf.threat_type.upper()} detected at {zone.full_location}. "
            f"Respond immediately. {clsf.description}"
        )
    return state
