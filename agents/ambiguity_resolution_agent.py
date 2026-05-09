import json
from services.llm_service import llm


def resolve_ambiguities_llm(requirements, ambiguities):

    prompt = f"""
You are a requirements engineering expert.

For each ambiguity:
- Provide 2–3 resolution options
- Options must be measurable and testable
- Provide one recommended option

Return STRICT JSON:

{{
  "step": "ambiguity_options",
  "options": [
    {{
      "req_id": "REQ-001",
      "question": "...",
      "choices": ["...", "..."],
      "recommended": "..."
    }}
  ]
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
            "step": "ambiguity_options",
            "options": []
        }
