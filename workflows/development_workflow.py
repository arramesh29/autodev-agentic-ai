import json

from langfuse import observe
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake


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

    # Step 5: Build with cmake
    generate_cmake(files)

    # Step 6: Return readable API response
    return {
        "generated_files": [f["filename"] for f in files],
        "output_directory": "generated/"
    }
