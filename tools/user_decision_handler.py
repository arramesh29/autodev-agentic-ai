def apply_user_choices(requirements, user_choices):

    updated_requirements = requirements.copy()

    next_id = len(requirements) + 1

    for choice in user_choices:

        new_req = {
            "id": f"REQ-{str(next_id).zfill(3)}",
            "description": choice["selected_option"],
            "type": "derived",
            "priority": "high",
            "atomic": True,
            "testable": True,
            "tags": ["user-selected"]
        }

        updated_requirements.append(new_req)
        next_id += 1

    return updated_requirements