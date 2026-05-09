def apply_user_choices(requirements, decisions):

    updated = requirements.copy()
    next_id = len(requirements) + 1

    for d in decisions:
        updated.append({
            "id": f"REQ-{str(next_id).zfill(3)}",
            "description": d.get("decision"),
            "type": "derived",
            "priority": "high",
            "atomic": True,
            "testable": True,
            "tags": ["user-selected"]
        })
        next_id += 1

    return updated
