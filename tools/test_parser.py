import re


def parse_ctest_output(output: str):

    result = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "raw": output
    }

    # Total tests
    total_match = re.search(r"(\d+)\s+tests? passed", output)
    failed_match = re.search(r"(\d+)\s+tests? failed", output)

    # Alternative pattern
    summary_match = re.search(
        r"(\d+)% tests passed,\s+(\d+) tests? failed out of (\d+)",
        output
    )

    if summary_match:
        percent, failed, total = summary_match.groups()
        result["total"] = int(total)
        result["failed"] = int(failed)
        result["passed"] = result["total"] - result["failed"]

    else:
        if total_match:
            result["passed"] = int(total_match.group(1))

        if failed_match:
            result["failed"] = int(failed_match.group(1))

        result["total"] = result["passed"] + result["failed"]

    return result
