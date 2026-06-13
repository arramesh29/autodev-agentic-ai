import json
import re
from services.llm_service import llm
from tools.rag.rag_orchestrator import retrieve_context

def safe_json_extract(text):

    cleaned = (
        text
        .replace("```json", "")
        .replace("```", "")
    )

    match = re.search(
        r"\{.*\}",
        cleaned,
        re.DOTALL
    )

    if not match:
        return None

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except:
        return None


def resolve_conflicts_llm(requirements, conflicts):

    # =====================================================
    # 🔥 RAG CONTEXT
    # =====================================================
    rag_context = retrieve_context(
        json.dumps(conflicts),
        "conflict"
    )

    prompt = f"""
You are a senior automotive systems engineer.

REFERENCE CONTEXT:
{rag_context}

Resolve requirement conflicts.

Rules:
- Do NOT remove requirements
- Do NOT create new requirement IDs
- Preserve all original requirement IDs
- Add clarifications, notes, assumptions,
  precedence rules, or metadata only to existing requirements 
- Requirement count must remain unchanged
- Define precedence rules clearly
- Use AIS/SPICE regulations if relevant
- Be logically consistent

Return STRICT JSON:

{{
  "resolved_requirements": [...],
  "resolution_log": [
    {{
      "conflict": ["REQ-001", "REQ-002"],
      "resolution": "...",
      "action": "derived_requirement | priority_rule | clarification_needed",
      "confidence": "high | medium | low"
    }}
  ],
  "needs_user_input": true/false,
  "questions": ["..."]
}}

Requirements:
{json.dumps(requirements, indent=2)}

Conflicts:
{json.dumps(conflicts, indent=2)}
"""

    response = llm.invoke(prompt)

    text = response.content.strip()

    parsed = safe_json_extract(text)
    
    if not parsed:
    
        print(
            "Conflict resolution JSON parse failed"
        )
    
        return {
            "resolved_requirements": requirements,
            "resolution_log": [],
            "needs_user_input": True,
            "questions": [
                "Unable to resolve conflicts automatically"
            ]
        }
    
    resolved = parsed.get(
        "resolved_requirements",
        []
    )

    if len(resolved) < len(requirements):
    
        print(
            "WARNING: Conflict resolution "
            "reduced requirement count"
        )
    
        parsed["resolved_requirements"] = requirements    
    
    if parsed:
        parsed["conflicts_resolved"] = len(
            parsed.get(
                "resolution_log",
                []
            )
        )
        return parsed
    
    print(
        "Conflict resolution JSON parse failed"
    )
    
    return {
        "resolved_requirements": requirements,
        "resolution_log": [],
        "needs_user_input": True,
        "questions": [
            "Unable to resolve conflicts automatically"
        ]
    }
