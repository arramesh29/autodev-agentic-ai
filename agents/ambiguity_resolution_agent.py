import json
from services.llm_service import llm


def resolve_ambiguities_llm(requirements, ambiguities):

    prompt = f"""
You are a requirements engineering expert.

For each ambiguity:
- Provide 2–3 reasonable resolution options
- Options must be measurable and testable
- Do NOT assume final choice — let user decide

Return STRICT JSON:

{{
  "ambiguity_options": [
    {{
      "req_id": "REQ-001",
      "issue": "...",
      "options": [
        "Option 1...",
        "Option 2...",
        "Option 3..."
      ],
      "recommended_option": "Option 1"
    }}
  ],
  "needs_user_input": true
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
            "ambiguity_options": [],
            "needs_user_input": True
        }
