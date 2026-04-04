import re


def parse_ctest_output(output: str):

    result = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "failed_tests": [],
        "failure_details": [],
        "summary": "",
        "raw": output
    }

    # ---- Summary parsing ----
    total_match = re.search(r"(\d+)\s+tests? passed", output)
    failed_match = re.search(r"(\d+)\s+tests? failed", output)

    summary_match = re.search(
        r"(\d+)% tests passed,\s+(\d+) tests? failed out of (\d+)",
        output
    )

    if summary_match:
        _, failed, total = summary_match.groups()
        result["total"] = int(total)
        result["failed"] = int(failed)
        result["passed"] = result["total"] - result["failed"]
    else:
        if total_match:
            result["passed"] = int(total_match.group(1))

        if failed_match:
            result["failed"] = int(failed_match.group(1))

        result["total"] = result["passed"] + result["failed"]

    # Extract FAILED test lines ----
    failed_lines = []
    for line in output.splitlines():
        if "FAILED" in line or "Failed" in line:
            failed_lines.append(line.strip())

    result["failed_tests"] = failed_lines

    # Extract failure details ----
    error_blocks = []
    current_block = []

    for line in output.splitlines():
        if any(x in line.lower() for x in ["error", "expected", "assert"]):
            current_block.append(line.strip())
        elif current_block:
            error_blocks.append(" ".join(current_block))
            current_block = []

    if current_block:
        error_blocks.append(" ".join(current_block))

    result["failure_details"] = error_blocks[:5]

    # Human-readable summary ----
    summary_parts = []

    if result["failed_tests"]:
        summary_parts.append("Failed Tests:")
        summary_parts.extend(result["failed_tests"][:3])

    if result["failure_details"]:
        summary_parts.append("\nFailure Reasons:")
        summary_parts.extend(result["failure_details"][:3])

    result["summary"] = "\n".join(summary_parts)

    return result
