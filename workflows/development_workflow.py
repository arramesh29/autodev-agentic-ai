import json

from langfuse import observe
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code
from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake
from tools.build_tool import build_and_test

# 🔥 NEW IMPORTS
from tools.test_parser import parse_ctest_output
from tools.confidence_scorer import compute_confidence


@observe()
def run_workflow(requirement):

    logs = []

    # Step 1: Create development plan
    plan = create_plan(requirement)

    # Step 2: Generate C++ code and tests
    result = generate_code(plan)

    # Step 3: Extract files
    files = result.get("files", [])

    if not files:
        return {"error": "No files generated"}

    # Step 4: Write files to disk
    write_files(files)

    # Step 5: Generate CMake
    generate_cmake(files)

    MAX_RETRIES = 5

    # 🔁 Step 6: Build + Debug Loop
    for attempt in range(MAX_RETRIES):

        logs.append(f"\n=== Attempt {attempt} ===")

        output = build_and_test()

        # 🔥 STEP 1: Parse structured test results
        parsed = parse_ctest_output(output)
        confidence = compute_confidence(parsed)

        logs.append(f"📊 Test Summary: {parsed}")
        logs.append(f"📈 Confidence Score: {confidence['confidence_score']}")

        # ✅ SUCCESS CONDITION (STRICT)
        if confidence["status"] == "success":
            logs.append("✅ All tests passed with high confidence")

            return {
                "status": "success",
                "generated_files": [f["filename"] for f in files],
                "test_summary": parsed,
                "confidence": confidence,
                "execution_log": logs
            }

        # ❌ NO TESTS CASE
        if confidence["status"] == "no_tests":
            logs.append("❌ No tests were executed — retrying")
        
        # ❌ FAILURE CASE
        else:
            logs.append("❌ Tests failed or insufficient confidence")

        # 🔍 Better failure classification
        if "error c" in output.lower() or "nmake" in output.lower():
            reason = "Compilation/Build Error"
        elif parsed["failed"] > 0:
            reason = "Test Failure (Logic Error)"
        else:
            reason = "Unknown Issue"

        logs.append(f"🔍 Reason: {reason}")

        # 👉 Add human-readable hints
        if "shouldinitiatebraking" in output.lower():
            logs.append("👉 Braking condition logic incorrect")

        if "deceleration" in output.lower():
            logs.append("👉 Deceleration calculation incorrect or zero")

        logs.append("🔧 Debug agent attempting fix...")

        try:
            files = fix_code(output, files)
            write_files(files)
            logs.append("✅ Fix applied")

        except Exception as e:
            logs.append(f"❌ Debug agent failed: {str(e)}")

            return {
                "status": "debug_failed",
                "execution_log": logs
            }

    # ❌ FINAL FAILURE
    return {
        "status": "failed_after_retries",
        "execution_log": logs
    }
