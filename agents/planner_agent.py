from services.llm_service import llm
import json
import re
from tools.rag.rag_orchestrator import retrieve_context

def _extract_json(text):

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

    try:
        return json.loads(
            match.group(0)
        )
    except:
        return None

def create_plan(requirements, trace=None, parent_span=None):

    if not requirements:
        raise ValueError("No requirements provided to planner")

    span = None

    if trace:
        span = (
            parent_span.span(name="create_plan_agent")
            if parent_span
            else trace.span(name="create_plan_agent")
        )

    formatted_requirements = ""

    for r in requirements:
        formatted_requirements += (
            f"{r['id']} "
            f"[{r.get('type','functional')}] "
            f"[{r.get('priority','medium')}]: "
            f"{r['description']}\n"
        )

    # =====================================================
    # 🔥 RAG CONTEXT
    # =====================================================
    rag_context = retrieve_context(
        formatted_requirements,
        "planner"
    )

    prompt = f"""
You are an automotive software architect.

REFERENCE CONTEXT:
{rag_context}

Convert the following structured requirements into a
clear software development plan.

Requirements:
{formatted_requirements}

Instructions:
1. Group requirements into modules
2. Define:
   - functions
   - interfaces
   - data flow
3. Ensure traceability:
   - Map each module/function to REQ-ID
4. Identify test scenarios per requirement

IMPORTANT:

Use ONLY requirement IDs provided.
Do NOT invent new requirement IDs.
Every requirement must appear exactly once.
Requirement count must remain unchanged.

Output format:
Return STRICT JSON only.

{{
  "modules": [
    {{
      "name": "Perception",
      "requirements": [
        "REQ-001",
        "REQ-002"
      ],
      "functions": [
        {{
          "name": "ProcessSensorInputs",
          "inputs": [
            "radar_tracks",
            "camera_objects"
          ],
          "outputs": [
            "tracked_objects"
          ]
        }}
      ],
      "test_cases": [
        "RadarObjectDetected",
        "CameraFusionWorks"
      ]
    }}
  ]
}}
"""

    generation = None
    output = None

    try:

        if span:
            generation = span.generation(
                name="llm_create_plan",
                model="gpt-4o",
                input=prompt,
                metadata={"agent": "planner_agent"}
            )

        response = llm.invoke(prompt)

        output = response.content

        parsed = _extract_json(output)

        planned_reqs = set()
        
        for module in parsed.get("modules", []):
        
            planned_reqs.update(
                module.get("requirements", [])
            )
        
        original_reqs = {
            r["id"]
            for r in requirements
        }
        
        missing = original_reqs - planned_reqs
        
        if missing:
        
            raise ValueError(
                f"Planner lost requirements: {missing}"
            )
        
        if not parsed:
            raise ValueError(
                "Planner returned invalid JSON"
            )
        
        plan = parsed
        
        if generation:
            generation.end(
                output=json.dumps(plan)[:2000]
            )
        
        if span:
            span.end(
                output=json.dumps(plan)[:1000]
            )
        
        return plan

    except Exception as e:

        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": output[:2000]
                    if output else "no response"
                }
            )

        if span:
            span.end(level="ERROR", status_message=str(e))

        raise
