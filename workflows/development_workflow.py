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


# 🔥 STRONG NORMALIZE (FIXED)
def normalize_files(files):

    # handle dict wrapper
    if isinstance(files, dict):
        if "files" in files:
            files = files["files"]
        else:
            files = [files]

    if not isinstance(files, list):
        print("SENDING: {'step': 'normalize_invalid_input'}")
        return []

    normalized = []

    for idx, f in enumerate(files):

        if not isinstance(f, dict):
            print(f"SENDING: {{'step': 'normalize_invalid_item', 'index': {idx}}}")
            continue

        filename = f.get("filename")
        content = f.get("content")

        if not isinstance(filename, str) or not filename.strip():
            print(f"SENDING: {{'step': 'normalize_invalid_filename', 'index': {idx}}}")
            continue

        if not isinstance(content, str):
            print(f"SENDING: {{'step': 'normalize_invalid_content', 'file': '{filename}'}}")
            continue

        normalized.append({
            "filename": filename.strip(),
            "content": content
        })

    print(f"SENDING: {{'step': 'normalize_success', 'count': {len(normalized)}}}")

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

        print(f"🔥 WORKFLOW LOOP attempt={attempt}")
        
        send_step("build_attempt", {
            "attempt": attempt,
            "source": "workflow",
            "execution_id": trace.id if trace else "no-trace"
        })

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
        send_step("debug_llm_call_start")

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

        send_step("debug_llm_call_end")

        # 🔥 DEBUG RESULT TYPE
        send_step("debug_result_type", {
            "type": str(type(fix_result))
        })

        updated_files = None

        if isinstance(fix_result, dict):
            candidate = fix_result.get("files")

            send_step("debug_files_pre_normalize", {
                "type": str(type(candidate)),
                "length": len(candidate) if isinstance(candidate, list) else "invalid"
            })

            if isinstance(candidate, list):
                updated_files = candidate

        # 🔥 STRICT FALLBACK
        if not isinstance(updated_files, list) or len(updated_files) == 0:
            send_step("debug_invalid_output_fallback")
            updated_files = files
        else:
            send_step("debug_valid_output", {"count": len(updated_files)})

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

        files = normalized_files

    send_step("failed")
