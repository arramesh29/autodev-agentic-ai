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


# 🔥 FINAL STRONG NORMALIZE (HARDENED)
def normalize_files(files):

    # 🔥 CRITICAL FIX: extract nested "files"
    if isinstance(files, dict):
        if "files" in files and isinstance(files["files"], list):
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
    
    
    def normalize_files(files):
    
        # 🔥 FIX: unwrap dict properly
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
    
    
    # 🔥 INSIDE run_workflow LOOP — ONLY MODIFY THIS PART
    
    last_failure_signature = None
    
    for attempt in range(MAX_RETRIES):
    
        send_step("build_attempt", {
            "attempt": attempt,
            "source": "workflow"
        })
    
        clean_build_folder()
        generate_cmake(files)
    
        output = build_and_test()
    
        parsed = parse_ctest_output(output) or {"failed": 1}
    
        send_step("test_result", {"parsed": parsed})
    
        if parsed.get("failed", 1) == 0:
            send_step("success")
            return
    
        # 🔥 NEW: stagnation detection
        signature = str(parsed.get("failure_details"))
    
        if signature == last_failure_signature:
            send_step("stagnation_detected")
            break
    
        last_failure_signature = signature
    
        # =========================
        # DEBUG
        # =========================
        fix_result = fix_code(parsed.get("summary"), files)
    
        # 🔥 CRITICAL FIX
        updated_files = normalize_files(fix_result)
    
        if not updated_files:
            send_step("debug_invalid_output_fallback")
            break
    
        send_step("debug_valid_output", {"count": len(updated_files)})
    
        # =========================
        # WRITE
        # =========================
        write_result = write_files(updated_files)
    
        send_step("write_result", write_result)
    
        files = updated_files
    
    send_step("failed")
