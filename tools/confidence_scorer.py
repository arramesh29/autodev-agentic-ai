def compute_confidence(test_result: dict):

    total = test_result.get("total", 0)
    passed = test_result.get("passed", 0)
    failed = test_result.get("failed", 0)

    if total == 0:
        return {
            "confidence_score": 0.0,
            "status": "no_tests"
        }

    pass_ratio = passed / total

    # Base score
    score = pass_ratio

    # Penalize failures
    if failed > 0:
        score -= 0.2

    # Clamp between 0 and 1
    score = max(0.0, min(score, 1.0))

    # Decision
    if score == 1.0:
        status = "success"
    elif score > 0.7:
        status = "partial"
    else:
        status = "retry"

    return {
        "confidence_score": round(score, 2),
        "status": status
    }