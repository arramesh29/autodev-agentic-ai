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
    structured_logs = []   # 🔥 NEW

    # Step 1: Create development plan
    plan = create_plan(requirement)

    logs.append("📋 Plan created")
    structured_logs.append({
        "step": "planning",
        "status": "success",
        "output": plan
    })

    # Step 2: Generate C++ code and tests
    result = generate_code(plan)
    files = result.get("files", [])

    if not files:
        return {
            "status": "error",
            "action": "generate_code",
            "data": None,
            "logs": logs,
            "structured_logs": structured_logs,
            "error": "No files generated"
        }

    structured_logs.append({
        "step": "code_generation",
        "status": "success",
        "file_count": len(files)
    })

    # Step 4: Write files to disk
    write_files(files)
    logs.append("📁 Files written")

    # Step 5: Generate CMake
    generate_cmake(files)
    logs.append("⚙️ CMake generated")

    MAX_RETRIES = 5

    # 🔁 Step 6: Build + Debug Loop
    for attempt in range(MAX_RETRIES):

        logs.append(f"\n=== Attempt {attempt} ===")

        structured_logs.append({
            "step": "attempt",
            "attempt_number": attempt
        })

        output = build_and_test()

        # 🔥 STEP 1: Parse structured test results
        parsed = parse_ctest_output(output)
        confidence = compute_confidence(parsed)

        logs.append(f"📊 Test Summary: {parsed}")
        logs.append(f"📈 Confidence Score: {confidence['confidence_score']}")

        structured_logs.append({
            "step": "test_analysis",
            "parsed": parsed,
            "confidence": confidence
        })

        # ✅ SUCCESS CONDITION
        if confidence["status"] == "success":
            logs.append("✅ All tests passed with high confidence")

            return {
                "status": "success",
                "action": "autodev_workflow",
                "data": {
                    "summary": "Code generated, tested, and validated successfully",
                    "generated_files": [f["filename"] for f in files],
                    "test_summary": parsed,
                    "confidence": confidence,
                    "attempts": attempt + 1
                },
                "logs": logs,
                "structured_logs": structured_logs,
                "error": None
            }

        # ❌ NO TESTS CASE
        if confidence["status"] == "no_tests":
            logs.append("❌ No tests were executed — retrying")
            reason = "No Tests Executed"

        else:
            logs.append("❌ Tests failed or insufficient confidence")

            if "error c" in output.lower() or "nmake" in output.lower():
                reason = "Compilation/Build Error"
            elif parsed["failed"] > 0:
                reason = "Test Failure (Logic Error)"
            else:
                reason = "Unknown Issue"

        logs.append(f"🔍 Reason: {reason}")

        structured_logs.append({
            "step": "failure_analysis",
            "reason": reason
        })

        # 👉 Human-readable hints
        if "shouldinitiatebraking" in output.lower():
            logs.append("👉 Braking condition logic incorrect")

        if "deceleration" in output.lower():
            logs.append("👉 Deceleration calculation incorrect or zero")

        logs.append("🔧 Debug agent attempting fix...")

        try:
            files = fix_code(output, files)
            write_files(files)

            logs.append("✅ Fix applied")

            structured_logs.append({
                "step": "debug",
                "status": "fix_applied"
            })

        except Exception as e:
            logs.append(f"❌ Debug agent failed: {str(e)}")

            return {
                "status": "error",
                "action": "debug_code",
                "data": {
                    "summary": "Debug agent failed",
                    "generated_files": [f["filename"] for f in files]
                },
                "logs": logs,
                "structured_logs": structured_logs,
                "error": str(e)
            }

    # ❌ FINAL FAILURE
    return {
        "status": "error",
        "action": "autodev_workflow",
        "data": {
            "summary": "Failed after max retries",
            "generated_files": [f["filename"] for f in files],
            "attempts": MAX_RETRIES
        },
        "logs": logs,
        "structured_logs": structured_logs,
        "error": "Max retries exceeded"
    }
