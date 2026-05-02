import json
from services.llm_service import llm

def analyze_requirements(raw_requirement):

    prompt = f"""
    Analyze automotive requirement and return STRICT JSON:

    Tasks:
    - Split into atomic requirements
    - Assign ID: REQ-XXX
    - Mark testable = true
    - Tag: functional / safety / performance
    - Detect conflicts
    - Detect ambiguities

    Requirement:
    {raw_requirement}

    JSON format example:
	{
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
	
    """

    response = llm(prompt)

    return json.loads(response)