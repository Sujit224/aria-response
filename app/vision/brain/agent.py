"""
brain/agent.py
LangGraph based Threat Analysis Agent

Flow:
  Alert Dict (from any detector)
       ↓
  [Node 1] validate_alert     → Check karo alert valid hai
       ↓
  [Node 2] build_prompt       → Minimalist prompt banao (token saving)
       ↓
  [Node 3] call_llm           → LLM ko call karo
       ↓
  [Node 4] format_response    → Output clean karo
       ↓
  Final ThreatMessage

Future expansion:
  [Node 5] notify_security    → Security ko message bhejo
  [Node 6] log_to_database    → Database mein save karo
  [Node 7] escalate           → Senior authority ko alert karo
"""

import os
import json
import time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.vision import config

# ══════════════════════════════════════════════════
#  LLM SETUP - Groq (free) ya OpenAI
# ══════════════════════════════════════════════════
def _load_llm():
    provider = config.LLM_PROVIDER.lower()

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                model       = "llama3-8b-8192",
                api_key     = os.getenv("GROQ_API_KEY"),
                temperature = config.LLM_TEMPERATURE,
                max_tokens  = config.LLM_MAX_TOKENS,
            )
            print("  [Agent] ✅ LLM: Groq llama3-8b connected")
            return llm
        except Exception as e:
            print(f"  [Agent] ⚠ Groq failed: {e}")

    if provider == "openai" or provider == "groq":
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model       = "gpt-3.5-turbo",
                api_key     = os.getenv("OPENAI_API_KEY"),
                temperature = config.LLM_TEMPERATURE,
                max_tokens  = config.LLM_MAX_TOKENS,
            )
            print("  [Agent] ✅ LLM: OpenAI gpt-3.5-turbo connected")
            return llm
        except Exception as e:
            print(f"  [Agent] ⚠ OpenAI failed: {e}")

    print("  [Agent] ⚠ No LLM connected - using rule-based fallback")
    return None


# ══════════════════════════════════════════════════
#  LANGGRAPH STATE
#  Ye dict poore graph mein pass hoti hai
# ══════════════════════════════════════════════════
class ThreatState(TypedDict):
    # ── Input (detector se aata hai) ──
    source         : str           # "weapon_detector", "smoke_detector", etc.
    detect_type    : str           # "GUN", "FIRE", "SMOKE", "ABANDONED_BAG", etc.
    confidence     : float         # 0.0 - 1.0
    location       : str           # "Top-Left", "Center", etc.
    priority       : str           # "CRITICAL", "HIGH", "MEDIUM"
    extra_info     : dict          # Additional info (track_id, static_seconds, etc.)

    # ── Intermediate (graph ke nodes fill karte hain) ──
    is_valid       : bool          # validate_alert node set karta hai
    reject_reason  : Optional[str] # Agar invalid to kyun
    prompt_text    : Optional[str] # build_prompt node set karta hai
    raw_llm_output : Optional[str] # call_llm node set karta hai

    # ── Final Output ──
    threat_level   : Optional[str]  # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW"
    threat_message : Optional[str]  # LLM ka main message
    action_required: Optional[str]  # Security ko kya karna chahiye
    timestamp      : Optional[str]  # Kab hua


# ══════════════════════════════════════════════════
#  NODE 1: validate_alert
#  Check karo alert sach mein LLM ke layak hai
# ══════════════════════════════════════════════════
def validate_alert(state: ThreatState) -> ThreatState:
    """
    Validation Rules:
    1. confidence 0.0 se 1.0 ke beech honi chahiye
    2. detect_type empty nahi hona chahiye
    3. source recognized hona chahiye
    4. Agar ye sab pass ho tabhi LLM ko disturb karo

    Ye node token waste rokta hai - garbage input pe LLM call nahi hogi
    """
    print(f"\n  [Agent Node 1] Validating alert: {state['detect_type']} from {state['source']}")

    # Check 1: Confidence range
    conf = state.get("confidence", 0)
    if not (0.0 < conf <= 1.0):
        state["is_valid"]      = False
        state["reject_reason"] = f"Invalid confidence: {conf}"
        print(f"  [Agent] ❌ Rejected: {state['reject_reason']}")
        return state

    # Check 2: Type present hai?
    if not state.get("detect_type", "").strip():
        state["is_valid"]      = False
        state["reject_reason"] = "detect_type empty hai"
        print(f"  [Agent] ❌ Rejected: {state['reject_reason']}")
        return state

    # Check 3: Known source hai?
    known_sources = ["weapon_detector", "smoke_detector", "bag_detector", "scan_detector"]
    if state.get("source") not in known_sources:
        state["is_valid"]      = False
        state["reject_reason"] = f"Unknown source: {state['source']}"
        print(f"  [Agent] ❌ Rejected: {state['reject_reason']}")
        return state

    # Sab pass ✅
    state["is_valid"]      = True
    state["reject_reason"] = None
    print(f"  [Agent Node 1] ✅ Validation passed")
    return state


# ══════════════════════════════════════════════════
#  NODE 2: build_prompt
#  Token-saving minimalist prompt banao
# ══════════════════════════════════════════════════
def build_prompt(state: ThreatState) -> ThreatState:
    """
    Minimalist prompt strategy:
    - LLM ko lamba paragraph nahi dena
    - Sirf zaroori metadata bhejte hain
    - JSON format mein response maango (easy to parse)
    - Max 200 tokens response (config se)

    Har detector ka alag context hota hai:
    - Weapon → immediate threat
    - Smoke  → fire hazard
    - Bag    → abandoned object
    - Scan   → X-ray weapon
    """
    det_type  = state["detect_type"]
    source    = state["source"]
    conf_pct  = int(state["confidence"] * 100)
    location  = state["location"]
    priority  = state["priority"]
    extra     = state.get("extra_info", {})

    # ── Source ke hisaab se context line ──
    if source == "weapon_detector":
        context = f"A {det_type} was visually detected by surveillance camera."
    elif source == "smoke_detector":
        context = f"{det_type} was detected by fire surveillance system (confirmed across multiple frames)."
    elif source == "bag_detector":
        secs = extra.get("static_seconds", config.BAG_STATIC_SECONDS)
        tid  = extra.get("track_id", "?")
        context = f"An unattended bag (Track ID: {tid}) has been stationary for {secs} seconds."
    elif source == "scan_detector":
        img = extra.get("image_file", "unknown")
        context = f"A {det_type} was detected in X-ray baggage scan (file: {img})."
    else:
        context = f"{det_type} detected by security system."

    # ── Final Minimalist Prompt ──
    prompt = f"""You are a concise security threat assessment AI.

DETECTION METADATA:
- Type     : {det_type}
- Source   : {source}
- Confidence: {conf_pct}%
- Location : {location}
- Priority : {priority}
- Context  : {context}

Respond ONLY with this JSON (no extra text, no markdown):
{{
  "threat_level": "CRITICAL or HIGH or MEDIUM or LOW",
  "threat_message": "One clear sentence describing the threat",
  "action_required": "One specific immediate action for security personnel"
}}"""

    state["prompt_text"] = prompt
    print(f"  [Agent Node 2] ✅ Prompt built ({len(prompt)} chars)")
    return state


# ══════════════════════════════════════════════════
#  NODE 3: call_llm
#  LLM ko actual call karo
# ══════════════════════════════════════════════════
_llm = None   # Global - ek baar load, baar baar reuse

def call_llm(state: ThreatState) -> ThreatState:
    """
    LLM ko prompt bhejo, response lo.

    Fallback logic:
    - LLM available nahi? → Rule-based response banao
    - LLM fail ho gaya? → Rule-based response banao
    - JSON parse fail? → Raw text use karo

    Rule-based fallback:
    Ye ensure karta hai system LLM ke bina bhi kaam kare
    """
    global _llm
    if _llm is None:
        _llm = _load_llm()

    prompt = state["prompt_text"]

    # ── Try LLM ──
    if _llm is not None:
        try:
            print(f"  [Agent Node 3] 📤 LLM ko call kar raha hoon...")
            response = _llm.invoke(prompt)
            state["raw_llm_output"] = response.content.strip()
            print(f"  [Agent Node 3] 📥 LLM response mila")
            return state
        except Exception as e:
            print(f"  [Agent Node 3] ⚠ LLM call failed: {e} → Fallback use karunga")

    # ── Rule-based Fallback ──
    det_type = state["detect_type"]
    location = state["location"]
    conf_pct = int(state["confidence"] * 100)
    source   = state["source"]

    if source == "weapon_detector":
        level   = "CRITICAL"
        message = f"{det_type} detected at {location} with {conf_pct}% confidence. Immediate threat."
        action  = "Evacuate area and contact armed response unit immediately."
    elif source == "smoke_detector":
        level   = "CRITICAL"
        message = f"{det_type} confirmed at {location}. Fire hazard detected."
        action  = "Activate fire alarm, evacuate personnel, contact fire department."
    elif source == "bag_detector":
        secs  = state.get("extra_info", {}).get("static_seconds", 30)
        level   = "HIGH"
        message = f"Unattended bag at {location} for {secs} seconds. Potential threat."
        action  = "Do not touch. Clear area and contact bomb disposal unit."
    elif source == "scan_detector":
        level   = "CRITICAL"
        message = f"Weapon ({det_type}) detected in baggage scan at {location}."
        action  = "Stop passenger immediately. Contact security and law enforcement."
    else:
        level   = "HIGH"
        message = f"Threat detected: {det_type} at {location}."
        action  = "Security personnel respond immediately."

    state["raw_llm_output"] = json.dumps({
        "threat_level"  : level,
        "threat_message": message,
        "action_required": action
    })
    print(f"  [Agent Node 3] ✅ Rule-based fallback response ready")
    return state


# ══════════════════════════════════════════════════
#  NODE 4: format_response
#  LLM output ko clean karke final state mein daalo
# ══════════════════════════════════════════════════
def format_response(state: ThreatState) -> ThreatState:
    """
    LLM ka raw output parse karo.
    JSON milega ideally, warna plain text se extract karo.
    Timestamp add karo.
    """
    raw = state.get("raw_llm_output", "")

    # ── JSON parse karo ──
    try:
        # Markdown code blocks hata do agar hain
        clean = raw.replace("```json", "").replace("```", "").strip()
        data  = json.loads(clean)

        state["threat_level"]    = data.get("threat_level",    "HIGH")
        state["threat_message"]  = data.get("threat_message",  "Threat detected.")
        state["action_required"] = data.get("action_required", "Security respond immediately.")

    except (json.JSONDecodeError, Exception):
        # JSON nahi mila - plain text use karo
        state["threat_level"]    = state.get("priority", "HIGH")
        state["threat_message"]  = raw[:200] if raw else "Threat detected by security system."
        state["action_required"] = "Security personnel respond immediately."

    # Timestamp
    from datetime import datetime
    state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"  [Agent Node 4] ✅ Response formatted")
    print(f"  [Agent]  Level  : {state['threat_level']}")
    print(f"  [Agent]  Message: {state['threat_message']}")
    print(f"  [Agent]  Action : {state['action_required']}")
    return state


# ══════════════════════════════════════════════════
#  ROUTING - Validate ke baad kahan jaana hai
# ══════════════════════════════════════════════════
def route_after_validation(state: ThreatState) -> str:
    """
    Validation pass? → build_prompt par jao
    Validation fail? → END par jao (LLM call nahi hogi)
    """
    if state.get("is_valid"):
        return "build_prompt"
    return END


# ══════════════════════════════════════════════════
#  LANGGRAPH BUILD
# ══════════════════════════════════════════════════
def build_graph():
    graph = StateGraph(ThreatState)

    # Nodes add karo
    graph.add_node("validate_alert",   validate_alert)
    graph.add_node("build_prompt",     build_prompt)
    graph.add_node("call_llm",         call_llm)
    graph.add_node("format_response",  format_response)

    # Entry point
    graph.set_entry_point("validate_alert")

    # Edges
    graph.add_conditional_edges(
        "validate_alert",
        route_after_validation,
        {
            "build_prompt": "build_prompt",
            END            : END,
        }
    )
    graph.add_edge("build_prompt",    "call_llm")
    graph.add_edge("call_llm",        "format_response")
    graph.add_edge("format_response", END)

    # Future nodes yahan add honge:
    # graph.add_node("notify_security", notify_security)
    # graph.add_node("log_database",    log_to_database)
    # graph.add_edge("format_response", "notify_security")

    return graph.compile()


# ══════════════════════════════════════════════════
#  ThreatAgent - main.py yahi use karta hai
# ══════════════════════════════════════════════════
class ThreatAgent:
    def __init__(self):
        self.graph = build_graph()
        print("  [Agent] ✅ LangGraph compiled (4 nodes active)")
        print("  [Agent]    Node flow: validate → prompt → llm → format")

    def analyze(self, alert: dict) -> dict:
        """
        Alert dict lo, threat analysis return karo.

        Input (from any detector):
        {
          "source"     : "weapon_detector",
          "type"       : "GUN",
          "confidence" : 0.87,
          "location"   : "Center-Left",
          "priority"   : "CRITICAL",
          ... (extra fields)
        }

        Output:
        {
          "threat_level"   : "CRITICAL",
          "threat_message" : "...",
          "action_required": "...",
          "timestamp"      : "2024-01-01 12:00:00"
        }
        """
        # Alert dict ko ThreatState mein convert karo
        initial_state: ThreatState = {
            "source"        : alert.get("source",     "unknown"),
            "detect_type"   : alert.get("type",       "UNKNOWN"),
            "confidence"    : alert.get("confidence", 0.0),
            "location"      : alert.get("location",   "Unknown"),
            "priority"      : alert.get("priority",   "HIGH"),
            "extra_info"    : {k: v for k, v in alert.items()
                               if k not in ["source", "type", "confidence",
                                            "location", "priority", "bbox", "queued_at"]},
            "is_valid"      : False,
            "reject_reason" : None,
            "prompt_text"   : None,
            "raw_llm_output": None,
            "threat_level"  : None,
            "threat_message": None,
            "action_required": None,
            "timestamp"     : None,
        }

        # Graph run karo
        final_state = self.graph.invoke(initial_state)

        # Agar validation fail hua
        if not final_state.get("is_valid"):
            return {
                "threat_level"   : "INVALID",
                "threat_message" : f"Alert rejected: {final_state.get('reject_reason')}",
                "action_required": "No action needed.",
                "timestamp"      : "",
            }

        return {
            "threat_level"   : final_state["threat_level"],
            "threat_message" : final_state["threat_message"],
            "action_required": final_state["action_required"],
            "timestamp"      : final_state["timestamp"],
        }
