import json
from services.llm_service import llm


def resolve_ambiguities_llm(requirements, ambiguities):

    """
    Enhanced ambiguity resolver:
    - Uses LLM to generate options
    - Filters low-impact ambiguities automatically
    - Sends only critical ones to UI
    """

    prompt = f"""
You are a requirements engineering expert.

For each ambiguity:
- Provide 2–3 resolution options
- Provide one recommended option
- Assign a criticality score between 0 and 1
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

    # 🔥 FILTERING LOGIC
    HIGH_THRESHOLD = 0.6
    LOW_THRESHOLD = 0.3

    user_options = []
    auto_resolved = []

    for item in items:

        score = item.get("criticality", 0.5)
        question = item.get("question", "").lower()

        # 🔥 FORCE USER for safety-critical keywords
        if any(k in question for k in [
            "brake", "collision", "safety", "threshold", "override", "asil"
        ]):
            user_options.append(item)
            continue

        # 🔥 LOW → auto resolve
        if score < LOW_THRESHOLD:
            auto_resolved.append(item)
            continue

        # 🔥 HIGH → user
        if score >= HIGH_THRESHOLD:
            user_options.append(item)
            continue

        # 🔥 MEDIUM → default to LLM recommendation
        auto_resolved.append(item)

    # 🔥 APPLY AUTO RESOLUTIONS
    updated_requirements = apply_auto_resolutions(requirements, auto_resolved)

    # 🔥 IF NOTHING TO ASK → CONTINUE PIPELINE
    if not user_options:
        return {
            "step": "ambiguity_resolved_auto",
            "requirements": updated_requirements,
            "auto_resolved_count": len(auto_resolved)
        }

    # 🔥 PREPARE UI OPTIONS
    options = []

    for item in user_options:
        options.append({
            "question": item.get("question"),
            "choices": item.get("choices", []),
            "recommended": item.get("recommended")
        })

    return {
        "step": "ambiguity_options",
        "options": options,
        "auto_resolved_count": len(auto_resolved)
    }


# 🔥 APPLY AUTO RESOLUTIONS TO REQUIREMENTS
def apply_auto_resolutions(requirements, auto_resolved):

    for item in auto_resolved:
        question = item.get("question")
        recommended = item.get("recommended")

        # attach note (simple version)
        for req in requirements:
            req.setdefault("notes", []).append(
                f"Auto-resolved: {question} → {recommended}"
            )

    return requirements
