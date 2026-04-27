import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.models.schemas import PipelineState, NLPResult
from app.db.collections import save_chat_message

llm = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

SYSTEM_PROMPT = """You are a crisis detection classifier for a hotel emergency response system.

Analyze the guest or staff message and return ONLY a valid JSON object with these exact fields:
{
  "threat_type": one of ["medical", "fire", "security", "crowd", "none"],
  "confidence": float 0.0–1.0,
  "severity": one of ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"],
  "is_threat": true or false,
  "victim_entity": string or null,
  "symptom_entity": string or null
}

Rules:
- is_threat = true only if confidence >= 0.6 and threat_type != "none"
- "collapsed", "not breathing", "chest pain", "unconscious" → medical CRITICAL
- "fire", "smoke", "flames", "burning" → fire CRITICAL
- "weapon", "gun", "knife", "attack", "fight" → security CRITICAL
- "crowd", "stampede", "pushing" → crowd HIGH
- Complaints about noise, room temperature, food → threat_type "none"
- Return ONLY the JSON object. No markdown, no explanation."""


async def nlp_classifier_node(state: PipelineState) -> PipelineState:
    """
    Sends enriched message text to Claude.
    Writes ChatMessage document to Firestore.
    Sets state.is_threat flag for the routing conditional edge.
    """
    enriched = state.enriched

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Message: {enriched.raw_text}"),
    ])

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except Exception:
        parsed = {
            "threat_type": "none", "confidence": 0.0,
            "severity": "NONE", "is_threat": False,
            "victim_entity": None, "symptom_entity": None,
        }

    nlp = NLPResult(
        message_id     = enriched.message_id,
        session_id     = enriched.session_id,
        threat_type    = parsed.get("threat_type", "none"),
        confidence     = parsed.get("confidence", 0.0),
        severity       = parsed.get("severity", "NONE"),
        is_threat      = parsed.get("is_threat", False),
        victim_entity  = parsed.get("victim_entity"),
        symptom_entity = parsed.get("symptom_entity"),
        poi_id         = enriched.poi_id,
        room_number    = enriched.room_number,
        floor_id       = enriched.floor_id,
        floor_level    = enriched.floor_level,
        block_id       = enriched.block_id,
        block_code     = enriched.block_code,
        coord_x        = enriched.coord_x,
        coord_y        = enriched.coord_y,
        venue_id       = enriched.venue_id,
        raw_text       = enriched.raw_text,
    )

    # Persist ChatMessage to Firestore — always, threat or not
    await save_chat_message({
        "id":             enriched.message_id,
        "session_id":     enriched.session_id,
        "raw_text":       enriched.raw_text,
        "language":       enriched.language,
        "threat_type":    nlp.threat_type,
        "severity":       nlp.severity,
        "nlp_confidence": nlp.confidence,
        "victim_entity":  nlp.victim_entity,
        "symptom_entity": nlp.symptom_entity,
    })

    state.nlp       = nlp
    state.is_threat = nlp.is_threat
    return state