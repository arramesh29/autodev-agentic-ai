import json

from langfuse import observe
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code
from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake
from tools.build_tool import build_project


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
    build_output = ""

    # 🔁 Step 6: Build + Debug Loop
    for attempt in range(MAX_RETRIES):

        logs.append(f"\n=== Attempt {attempt} ===")

        output = build_and_test()

        # ✅ SUCCESS CONDITION
        if "failed" not in output.lower() and "error" not in output.lower():
            logs.append("✅ Build and all tests passed successfully")

            return {
                "status": "success",
                "generated_files": [f["filename"] for f in files],
                "execution_log": logs
            }

        # ❌ FAILURE
        logs.append("❌ Failure detected")
        logs.append(output[:1000])  # truncate for readability

        # Identify failure type
        if "error" in output.lower():
            reason = "Compilation/Build Error"
        else:
            reason = "Test Failure (Logic Error)"

        logs.append(f"🔍 Reason: {reason}")

        try:
            files = fix_code(output, files)
            write_files(files)
            logs.append("🔧 Fix applied by debug agent")

        except Exception as e:
            logs.append(f"❌ Debug agent failed: {str(e)}")

            return {
                "status": "debug_failed",
                "execution_log": logs
            }

    return {
        "status": "failed_after_retries",
        "execution_log": logs
    }
