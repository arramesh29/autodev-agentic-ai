import json
import os
import re


REQ_PATTERN = r"REQ-\d+"


def extract_reqs_from_files(files):

    implemented = set()

    for f in files:

        content = f.get("content", "")

        reqs = re.findall(
            REQ_PATTERN,
            content
        )

        implemented.update(reqs)

    return implemented


def validate_requirement_coverage(
    requirements,
    generated_files,
    output_path="generated/implementation_coverage.json"
):

    expected = set()

    for req in requirements or []:

        req_id = req.get("id")

        if req_id:
            expected.add(req_id)

    implemented = extract_reqs_from_files(
        generated_files
    )

    missing = sorted(
        list(expected - implemented)
    )

    extra = sorted(
        list(implemented - expected)
    )

    coverage = (
        round(
            len(expected.intersection(implemented))
            / max(len(expected), 1)
            * 100,
            2
        )
    )

    result = {
        "summary": {
            "requirements_total": len(expected),
            "implemented": len(
                expected.intersection(
                    implemented
                )
            ),
            "missing": len(missing),
            "coverage_percent": coverage
        },
        "implemented_requirements":
            sorted(list(implemented)),
        "missing_requirements":
            missing,
        "unexpected_requirements":
            extra
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

    return result