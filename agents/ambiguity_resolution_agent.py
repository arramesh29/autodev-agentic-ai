import json
from services.llm_service import llm


def resolve_ambiguities_llm(requirements, ambiguities):

    prompt = f"""
You are a requirements engineering expert.

Convert ambiguous requirements into measurable and testable ones.

Rules:
- Do NOT guess blindly
- Add derived requirements if needed
- If unclear → ask user

Return STRICT JSON:

{{
  "resolved_requirements": [...],
  "resolution_log": [
    {{
      "req_id": "REQ-001",
      "issue": "...",
      "resolution": "...",
      "confidence": "high | medium | low"
    }}
  ],
  "needs_user_input": true/false,
  "questions": ["..."]
}}

Requirements:
{json.dumps(requirements, indent=2)}

Ambiguities:
{json.dumps(ambiguities, indent=2)}
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
            "questions": ["Unable to resolve ambiguities automatically"]
        }