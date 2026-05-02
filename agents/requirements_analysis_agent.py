import json
from services.llm_service import llm


def analyze_requirements(raw_requirement):

    # ✅ Use JSON object instead of manual string
    example_output = {
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Compute time-to-collision",
                "type": "functional",
                "priority": "high",
                "atomic": True,
                "testable": True,
                "tags": ["AEB", "safety"]
            }
        ],
        "conflicts": [
            {
                "req_ids": ["REQ-002", "REQ-005"],
                "reason": "Conflicting braking thresholds"
            }
        ],
        "ambiguities": [
            {
                "req_id": "REQ-003",
                "issue": "Speed range not defined"
            }
        ]
    }

    prompt = f"""
Analyze automotive requirement and return STRICT JSON.

Tasks:
- Split into atomic requirements
- Assign ID: REQ-XXX
- Mark testable = true
- Tag: functional / safety / performance / Non functional / No requirement
- Detect conflicts
- Detect ambiguities

Requirement:
{raw_requirement}

Return output EXACTLY in this JSON format:

{json.dumps(example_output, indent=2)}

IMPORTANT:
- Use ONLY valid JSON (true/false, not True/False)
- No explanation
- No extra text
"""

    response = llm(prompt)

    # 🔥 SAFE PARSING
    try:
        return json.loads(response)
    except Exception:
        print("Invalid JSON from LLM:", response)
        return {
            "requirements": [],
            "conflicts": [],
            "ambiguities": []
        }
