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

    MAX_RETRIES = 3
    build_output = ""

    # 🔁 Step 6: Build + Debug Loop
    for attempt in range(MAX_RETRIES):

        print(f"Build attempt {attempt+1}")

        build_output = build_project()

        # ✅ If build successful
        if "error" not in build_output.lower():
            return {
                "status": "success",
                "generated_files": [f["filename"] for f in files],
                "output_directory": "generated/"
            }

        # ❌ Build failed → Debug Agent
        print("Build failed. Invoking debug agent...")

        try:
            files = fix_code(build_output, files)
            write_files(files)
        except Exception as e:
            return {
                "status": "debug_failed",
                "error": str(e),
                "build_log": build_output
            }

    # ❌ Failed after retries
    return {
        "status": "failed_after_retries",
        "build_log": build_output
    }
