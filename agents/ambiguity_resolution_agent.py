import json
from services.llm_service import llm

# 🔥 NEW
from tools.rag.rag_orchestrator import retrieve_context


def resolve_ambiguities_llm(requirements, ambiguities):

    """
    Enhanced ambiguity resolver:
    - Uses LLM + RAG
    - Filters low-impact ambiguities automatically
    - Sends only critical ones to UI
    """

    # =====================================================
    # 🔥 RAG CONTEXT
    # =====================================================
    rag_context = retrieve_context(
        json.dumps(ambiguities),
        "ambiguity"
    )

    prompt = f"""
You are a requirements engineering expert.

REFERENCE CONTEXT:
{rag_context}

For each ambiguity:
- Provide 2–3 resolution options
- Provide one recommended option
- If standards define value → auto resolve
- Assign criticality score between 0 and 1
  (0 = trivial, 1 = safety-critical)

Return STRICT JSON:

{{
  "items": [
    {{
      "req_id": "REQ-001",
      "question": "...",
      "choices": ["...", "..."],
      "recommended": "...",
      "criticality": 0.8
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
        parsed = json.loads(text)
        items = parsed.get("items", [])

    except:

        return {
            "step": "ambiguity_options",
            "options": []
        }

    HIGH_THRESHOLD = 0.6
    LOW_THRESHOLD = 0.3

    user_options = []
    auto_resolved = []

    for item in items:

        score = item.get("criticality", 0.5)

        question = item.get("question", "").lower()

        if any(k in question for k in [
            "brake",
            "collision",
            "safety",
            "threshold",
            "override",
            "asil"
        ]):
            user_options.append(item)
            continue

        if score < LOW_THRESHOLD:
            auto_resolved.append(item)
            continue

        if score >= HIGH_THRESHOLD:
            user_options.append(item)
            continue

        auto_resolved.append(item)

    updated_requirements = apply_auto_resolutions(
        requirements,
        auto_resolved
    )

    if not user_options:

        return {
            "step": "ambiguity_resolved_auto",
            "requirements": updated_requirements,
            "auto_resolved_count": len(auto_resolved)
        }

    options = []

    for item in user_options:

        options.append({
            "req_id": item.get("req_id"),
            "question": item.get("question"),
            "choices": item.get("choices", []),
            "recommended": item.get("recommended")
        })

    return {
        "step": "ambiguity_options",
        "options": options,
        "auto_resolved_count": len(auto_resolved),
        "auto_resolved": auto_resolved,
        "user_options": user_options,
        "user_resolution_required": len(user_options)
    }


def apply_auto_resolutions(requirements, auto_resolved):

    req_map = {
        r.get("id"): r
        for r in requirements
        if r.get("id")
    }

    for item in auto_resolved:

        req_id = item.get("req_id")

        if not req_id:
            continue

        req = req_map.get(req_id)

        if not req:
            continue

        req.setdefault(
            "clarifications",
            []
        )

        req["clarifications"].append({
            "question": item.get("question"),
            "resolution": item.get("recommended")
        })

    return requirements
