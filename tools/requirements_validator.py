def validate_requirements(data):

    validated = []

    for req in data.get("requirements", []):
        if not req.get("id") or not req.get("description"):
            continue

        req["atomic"] = True
        req["testable"] = True

        validated.append(req)

    return {
        "requirements": validated,
        "conflicts": data.get("conflicts", []),
        "ambiguities": data.get("ambiguities", [])
    }