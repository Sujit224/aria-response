import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.models.schemas import PipelineState, GeneratedMessages

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

SYSTEM_PROMPT = """You are the emergency communication engine for ARIA — a hotel crisis response system.

Given a resolved incident, generate role-specific messages. Return ONLY a JSON object:
{
  "msg_guest_ack": "Direct reply to the guest. Calm, reassuring. Confirm that an assistant is on the way to their exact location. Instruct them to open the door and not to panic.",
  "msg_staff_zone1": "Immediate action for zone 1 staff (same floor/block). Location, threat type, nearest aid kit.",
  "msg_staff_zone2": "Standby message for adjacent floor staff. Brief.",
  "msg_staff_zone3": "Awareness-only for other blocks. One sentence.",
  "msg_responder": "Structured brief for first responders. Location, threat, access route, victim info.",
  "dashboard_summary": "One-line ops summary. Format: SEVERITY | THREAT | LOCATION",
  "suggested_actions": ["action1", "action2", "action3"]
}

Always include block + room + floor in every location reference. Be factual and calm."""


async def llm_responder_node(state: PipelineState) -> PipelineState:
    zone = state.zone
    nlp  = state.nlp

    context = f"""
Incident:
- Threat: {zone.threat_type} | Severity: {zone.severity}
- Location: {zone.full_location}
- Nearest exit: {zone.nearest_exit_name}
- Nearest aid kit: {zone.nearest_aid_kit}
- Victim: {nlp.victim_entity or 'unknown'}
- Symptom: {nlp.symptom_entity or 'unknown'}
- Original message: "{nlp.raw_text}"
- Staff on floor: {len(zone.staff_on_floor)}
"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ])

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
    except Exception:
        result = {
            "msg_guest_ack":    f"We received your alert. An assistant is on the way to {zone.full_location}. Please open the door and don't panic.",
            "msg_staff_zone1":  f"ALERT: {zone.threat_type.upper()} at {zone.full_location}. Respond immediately.",
            "msg_staff_zone2":  f"Incident at {zone.full_location}. Stand by.",
            "msg_staff_zone3":  f"Advisory: incident Floor {zone.floor_level}, Block {zone.block_code}.",
            "msg_responder":    f"{zone.severity} {zone.threat_type} at {zone.full_location}. Access via {zone.nearest_exit_name}.",
            "dashboard_summary": f"{zone.severity} | {zone.threat_type} | {zone.full_location}",
            "suggested_actions": ["Dispatch zone 1 staff", "Alert emergency services", "Notify front desk"],
        }

    state.messages = GeneratedMessages(
        incident_id      = zone.incident_id,
        severity         = zone.severity,
        msg_guest_ack    = result.get("msg_guest_ack", ""),
        msg_staff_zone1  = result.get("msg_staff_zone1", ""),
        msg_staff_zone2  = result.get("msg_staff_zone2", ""),
        msg_staff_zone3  = result.get("msg_staff_zone3", ""),
        msg_responder    = result.get("msg_responder", ""),
        dashboard_summary = result.get("dashboard_summary", ""),
        suggested_actions = result.get("suggested_actions", []),
        session_id       = zone.session_id,
        venue_id         = zone.venue_id,
    )
    return state