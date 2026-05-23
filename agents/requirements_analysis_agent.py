import json
from services.llm_service import llm


from tools.rag.rag_orchestrator import retrieve_context


def analyze_requirements(raw_requirement):

    # =====================================================
    # 🔥 RAG CONTEXT
    # =====================================================
    rag_context = retrieve_context(
        raw_requirement,
        "requirements"
    )

    example_output = {
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Compute time-to-collision",
                "type": "functional",
                "priority": "high",
                "atomic": True,
                "testable": True,
                "tags": ["AEB", "safety"],
                "source": "AIS reference if applicable"
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
You are an automotive requirements engineering expert.

REFERENCE CONTEXT:
{rag_context}

Analyze automotive requirement and return STRICT JSON.

Tasks:
- Split into atomic requirements
- Assign ID: REQ-XXX
- Mark testable = true
- Tag: functional / safety / performance / Non functional / No requirement
- Detect conflicts
- Detect ambiguities
- Use AIS/SPICE standards if applicable
- Add source reference if regulation/spec used

Requirement:
{raw_requirement}

Return output EXACTLY in this JSON format:

{json.dumps(example_output, indent=2)}

IMPORTANT:
- Use ONLY valid JSON (true/false, not True/False)
- No explanation
- No extra text
"""

    response = llm.invoke(prompt)

    text = response.content.strip()

    try:
        return json.loads(text)
    except:
        print("Invalid JSON:", text)

        return {
            "requirements": [],
            "conflicts": [],
            "ambiguities": []
        }
