import os, asyncio, json
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatGroq(model='qwen-2.5-32b', api_key=os.getenv('GROQ_API_KEY'), temperature=0)

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

async def main():
    try:
        llm_old = ChatGroq(model='qwen-2.5-32b', api_key=os.getenv('GROQ_API_KEY'), temperature=0)
        res = await llm_old.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content='Message: EMERGENCY - I need immediate help! My husband has suddenly collapsed')
        ])
        print('RESPONSE qwen-2.5-32b:', repr(res.content))
    except Exception as e:
        print('ERROR qwen-2.5-32b:', e)

asyncio.run(main())
