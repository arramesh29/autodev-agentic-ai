import os
import shutil
from langfuse import Langfuse

from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code

from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake
from tools.build_tool import build_and_test

from tools.test_parser import parse_ctest_output
from tools.confidence_scorer import compute_confidence

from utils.logger import send_log, send_step


langfuse = Langfuse()


def extract_files_recursively(obj):
    extracted = []

    if isinstance(obj, dict):
        if "filename" in obj and "content" in obj:
            extracted.append(obj)
        elif "files" in obj:
            extracted.extend(extract_files_recursively(obj["files"]))

    elif isinstance(obj, list):
        for item in obj:
            extracted.extend(extract_files_recursively(item))

    return extracted


def clean_generated_folder():
    output_dir = "generated"
    if not os.path.exists(output_dir):
        return

    for f in os.listdir(output_dir):
        try:
            os.remove(os.path.join(output_dir, f))
        except Exception:
            pass


def clean_build_folder():
    build_dir = "autodev_build"

    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir)
            print("SENDING: {'step': 'build_cleaned'}")
        except Exception as e:
            print(f"SENDING: {{'step': 'build_clean_failed', 'error': '{str(e)}'}}")


# 🔥 FIXED NORMALIZE (handles dict also)
def normalize_files(files):

    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        return []

    normalized = []

    for f in files:
        if isinstance(f, dict):
            filename = f.get("filename")
            content = f.get("content")

            if isinstance(filename, str) and filename.strip() and isinstance(content, str):
                normalized.append({
                    "filename": filename.strip(),
                    "content": content
                })

    return normalized


def run_workflow(requirement):

    trace = langfuse.trace(
        name="autodev_workflow",
        input={"requirement": requirement},
        metadata={"system": "agentic-ai-dev"}
    )

    send_step("start")

    # =========================
    # PLAN
    # =========================
    plan = create_plan(requirement, trace=trace)
    send_step("plan_created")

    # =========================
    # CODE GENERATION
    # =========================
    result = generate_code(plan)

    files = extract_files_recursively(result.get("files", []))

    if not files:
        send_step("error", {"message": "Code generation failed"})
        return

    send_step("code_generated", {"files": [f["filename"] for f in files]})

    # =========================
    # INITIAL WRITE
    # =========================
    clean_generated_folder()

    send_step("initial_write")
    write_files(files)

    generate_cmake(files)

    # =========================
    # RETRY LOOP
    # =========================
    MAX_RETRIES = 3

    for attempt in range(MAX_RETRIES):

        send_step("build_attempt", {"attempt": attempt})

        clean_build_folder()
        generate_cmake(files)

        output = build_and_test()

        parsed = parse_ctest_output(output) or {"failed": 1}
        confidence = compute_confidence(parsed) or {"status": "retry"}

        send_step("test_result", {
            "parsed": parsed,
            "confidence": confidence
        })

        if confidence.get("status") == "success":
            send_step("success")
            return

        send_step("debug_start")

        # =========================
        # DEBUG
        # =========================
        fix_result = None

        try:
            fix_result = fix_code(
                parsed.get("summary"),
                files,
                trace=trace
            )
        except Exception as e:
            send_step("debug_error", {"message": str(e)})

        # 🔥 LOG RAW DEBUG OUTPUT TYPE
        send_step("debug_result_type", {
            "type": str(type(fix_result))
        })

        updated_files = None

        if isinstance(fix_result, dict):
            updated_files = fix_result.get("files")

        # 🔥 LOG BEFORE VALIDATION
        send_step("debug_files_raw", {
            "is_list": isinstance(updated_files, list),
            "length": len(updated_files) if isinstance(updated_files, list) else "invalid"
        })

        # 🔥 FALLBACK WITH VISIBILITY
        if not isinstance(updated_files, list) or len(updated_files) == 0:
            send_step("debug_fallback_to_previous_files")
            updated_files = files

        # =========================
        # NORMALIZE
        # =========================
        normalized_files = normalize_files(updated_files)

        send_step("normalized_files", {
            "count": len(normalized_files)
        })

        if not normalized_files:
            send_step("normalization_failed_fallback")
            normalized_files = files

        # =========================
        # WRITE
        # =========================
        send_step("write_attempt", {
            "file_count": len(normalized_files)
        })

        write_result = write_files(normalized_files)

        send_step("write_result", write_result)

        # =========================
        # STATE UPDATE
        # =========================
        files = normalized_files

    send_step("failed")
