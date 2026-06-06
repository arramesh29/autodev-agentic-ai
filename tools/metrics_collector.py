import json
import os
from datetime import datetime


def load_json(path):

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}


def generate_execution_metrics(
    requirements_file,
    coverage_file,
    traceability_file,
    output_file="generated/execution_metrics.json"
):

    requirements = load_json(requirements_file)

    coverage = load_json(coverage_file)

    traceability = load_json(traceability_file)

    metrics = {

        "timestamp":
            datetime.now().isoformat(),

        "requirements_total": 0,

        "requirements_implemented": 0,

        "requirements_linked": 0,

        "requirement_coverage": 0,

        "traceability_coverage": 0,

        "ambiguities_detected": 0,

        "ambiguities_resolved": 0,

        "conflicts_detected": 0,

        "conflicts_resolved": 0
    }

    # -----------------------------------
    # REQUIREMENTS
    # -----------------------------------

    final_reqs = requirements.get(
        "final_requirements",
        []
    )

    metrics["requirements_total"] = len(
        final_reqs
    )

    metrics["ambiguities_detected"] = len(
        requirements.get(
            "ambiguities",
            []
        )
    )

    metrics["conflicts_detected"] = len(
        requirements.get(
            "conflicts",
            []
        )
    )

    # -----------------------------------
    # COVERAGE
    # -----------------------------------

    coverage_summary = coverage.get(
        "summary",
        {}
    )

    metrics["requirements_implemented"] = (
        coverage_summary.get(
            "implemented",
            0
        )
    )

    metrics["requirement_coverage"] = (
        coverage_summary.get(
            "coverage_percent",
            0
        )
    )

    # -----------------------------------
    # TRACEABILITY
    # -----------------------------------

    trace_summary = traceability.get(
        "summary",
        {}
    )

    metrics["requirements_linked"] = (
        trace_summary.get(
            "requirements_linked",
            0
        )
    )

    metrics["traceability_coverage"] = (
        trace_summary.get(
            "traceability_coverage_percent",
            0
        )
    )

    # -----------------------------------
    # FUTURE PLACEHOLDERS
    # -----------------------------------

    metrics["ambiguities_resolved"] = 0

    metrics["conflicts_resolved"] = 0

    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metrics,
            f,
            indent=2
        )

    print(
        f"📊 Metrics generated: {output_file}"
    )

    return metrics