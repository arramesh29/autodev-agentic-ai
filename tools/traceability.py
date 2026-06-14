import json
import os
import re


REQ_PATTERN = r"REQ[-_]?\d+"

def normalize_req(req_id):

    digits = re.findall(r"\d+", req_id)

    if not digits:
        return req_id

    return f"REQ-{digits[0].zfill(3)}"

def generate_traceability(
    requirements,
    generated_files,
    output_path="generated/traceability.json"
):

    traceability = {}

    # ----------------------------------------
    # Initialize all requirements
    # ----------------------------------------
    for req in requirements or []:

        req_id = req.get("id")

        if not req_id:
            continue

        traceability[req_id] = {
            "description": req.get("description", ""),
            "code_files": [],
            "test_files": []
        }

    # ----------------------------------------
    # Scan generated files
    # ----------------------------------------
    for f in generated_files:

        filename = f.get("filename", "")
        content = f.get("content", "")

        req_ids = {
            normalize_req(r)
            for r in re.findall(
                REQ_PATTERN,
                content
            )
        }

        for req_id in req_ids:

            if req_id not in traceability:
                continue

            if filename.startswith("test_"):

                traceability[req_id]["test_files"].append(
                    filename
                )

            else:

                traceability[req_id]["code_files"].append(
                    filename
                )

    # ----------------------------------------
    # Coverage Metrics
    # ----------------------------------------
    total = len(traceability)

    linked = sum(
        1
        for v in traceability.values()
        if v["code_files"] and v["test_files"]
    )

    coverage = (
        round((linked / total) * 100, 2)
        if total
        else 0
    )

    result = {
        "summary": {
            "requirements_total": total,
            "requirements_linked": linked,
            "traceability_coverage_percent": coverage
        },
        "traceability": traceability
    }

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2
        )

    print(
        f"📌 Traceability generated: {output_path}"
    )

    return result
