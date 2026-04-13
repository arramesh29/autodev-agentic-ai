import os
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


def normalize_files(files):
    normalized = []

    if not isinstance(files, list):
        return normalized

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

    logs = []

    send_step("start")

    try:
        # =========================
        # PLAN
        # =========================
        plan = create_plan(requirement, trace=trace)
        send_step("plan_created")

        # =========================
        # CODE GEN
        # =========================
        result = generate_code(plan)

        files = extract_files_recursively(result.get("files", []))

        if not files:
            raise ValueError("Code generation failed")

        send_step("code_generated", {"files": [f["filename"] for f in files]})

        # INITIAL WRITE
        clean_generated_folder()
        write_files(files)

        generate_cmake(files)

        # =========================
        # RETRY LOOP
        # =========================
        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES):

            send_step("build_attempt", {"attempt": attempt})

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

            send_log(logs, "🔧 Debugging...")

            # =========================
            # DEBUG
            # =========================
            fix_result = fix_code(
                parsed.get("summary", output),
                files,
                trace=trace
            )

            updated_files = None

            if isinstance(fix_result, dict):
                updated_files = fix_result.get("files")

            send_log(logs, f"DEBUG RAW TYPE: {type(updated_files)}")

            # 🔥 FORCE VALID DATA
            if not isinstance(updated_files, list):
                send_log(logs, "⚠️ Invalid debug output → fallback")
                updated_files = files

            if not updated_files:
                send_log(logs, "⚠️ Empty debug output → fallback")
                updated_files = files

            # 🔥 NORMALIZE (NEVER SKIP)
            normalized_files = normalize_files(updated_files)

            if not normalized_files:
                send_log(logs, "⚠️ Normalization failed → fallback")
                normalized_files = files

            # 🔥🚨 GUARANTEED WRITE (NO CONTINUE ABOVE)
            send_log(logs, f"🔥 FORCED WRITE {len(normalized_files)} FILES")

            write_result = write_files(normalized_files)

            send_log(logs, f"🔥 WRITE RESULT → {write_result}")

            # 🔥 ALWAYS UPDATE STATE
            files = normalized_files

        send_step("failed")

    except Exception as e:
        send_step("error", {"message": str(e)})
        raise
