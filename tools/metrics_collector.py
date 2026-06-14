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
    ambiguity_result=None,
    conflict_result=None,
    test_result=None,
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
        "conflicts_resolved": 0,

        "tests_total": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "test_pass_percent": 0
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

    # -------------------------
    # Ambiguity metrics
    # -------------------------
    
    if ambiguity_result:
    
        auto_count = ambiguity_result.get(
            "auto_resolved_count",
            0
        )
    
        user_count = ambiguity_result.get(
            "user_resolution_required",
            0
        )
    
        metrics["ambiguities_resolved"] = (
            auto_count + user_count
        )
    
    # -------------------------
    # Conflict metrics
    # -------------------------
    
    if conflict_result:
    
        detected_conflicts = metrics[
            "conflicts_detected"
        ]
        
        resolved_conflicts = conflict_result.get(
            "conflicts_resolved"
        )
        
        if resolved_conflicts is None:
        
            resolved_conflicts = min(
                detected_conflicts,
                len(
                    conflict_result.get(
                        "resolved_conflicts",
                        []
                    )
                )
            )
        
        metrics["conflicts_resolved"] = (
            resolved_conflicts
        )

    if test_result:

        total = test_result.get("total", 0)
        passed = test_result.get("passed", 0)
    
        metrics["tests_total"] = total
        metrics["tests_passed"] = passed
        metrics["tests_failed"] = test_result.get(
            "failed",
            0
        )
    
        metrics["test_pass_percent"] = round(
            (passed / total) * 100,
            2
        ) if total else 0
    
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
