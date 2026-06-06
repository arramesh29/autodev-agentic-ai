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
    session_id,
    pipeline_status,
    requirements_file=None,
    coverage_file="generated/implementation_coverage.json",
    traceability_file="generated/traceability.json",
    output_file="generated/execution_metrics.json"
):

    metrics = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "pipeline_status": pipeline_status,

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

    requirements = load_json(requirements_file) \
        if requirements_file else {}

    coverage = load_json(coverage_file)

    traceability = load_json(traceability_file)

    metrics["requirements_total"] = len(
        requirements.get(
            "final_requirements",
            []
        )
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

    return metrics
