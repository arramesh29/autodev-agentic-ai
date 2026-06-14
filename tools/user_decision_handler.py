def apply_user_choices(requirements, decisions):

    req_map = {
        r.get("id"): r
        for r in requirements
        if r.get("id")
    }

    for d in decisions:

        req_id = d.get("req_id")

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
            "question": d.get(
                "question",
                ""
            ),
            "resolution":
                d.get("decision")
                or d.get("selected_option")
                or d.get("selected")
                or d.get("answer")
        })

    return list(req_map.values())
