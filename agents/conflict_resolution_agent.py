import json
from services.llm_service import llm

# 🔥 NEW
from tools.rag.rag_orchestrator import retrieve_context


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
- Add derived requirements if needed
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

    try:
        return json.loads(text)

    except:

        return {
            "resolved_requirements": requirements,
            "resolution_log": [],
            "needs_user_input": True,
            "questions": [
                "Unable to resolve conflicts automatically"
            ]
        }
