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
        # 🧠 PLAN
        # =========================
        plan_span = trace.span(name="planning")

        plan = create_plan(requirement, trace=trace, parent_span=plan_span)

        plan_span.end(output=plan)
        send_log(logs, "📋 Plan created")

        # =========================
        # ⚙️ CODE GEN
        # =========================
        code_span = trace.span(name="code_generation")

        required_files = {
            "aeb_controller.h",
            "aeb_controller.cpp",
            "test_aeb_controller.cpp"
        }

        MAX_GEN_RETRY = 2
        files = []

        for gen_attempt in range(MAX_GEN_RETRY):

            result = generate_code(plan)

            if not isinstance(result, dict):
                raise ValueError("generate_code returned invalid format")

            generated_files = extract_files_recursively(result.get("files", []))

            returned_files = set(f["filename"] for f in generated_files)
            missing = required_files - returned_files

            if not missing:
                files = generated_files
                break

            send_log(logs, f"⚠️ Generation attempt {gen_attempt} missing files: {missing}")

        if not files:
            raise ValueError("❌ Code generation failed")

        code_span.end(output={"file_count": len(files)})

        send_step("code_generated", {"files": [f["filename"] for f in files]})

        # =========================
        # INITIAL WRITE
        # =========================
        clean_generated_folder()
        write_result = write_files(files)

        send_log(logs, f"DEBUG: Initial write → {write_result}")

        if not write_result.get("success"):
            send_log(logs, f"⚠️ Initial write failed: {write_result.get('error')}")

        generate_cmake(files)

        send_log(logs, "📁 Files written")
        send_log(logs, "⚙️ CMake generated")

        # =========================
        # 🔁 RETRY LOOP
        # =========================
        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES):

            try:
                send_step("build_attempt", {"attempt": attempt})

                output = build_and_test()

                parsed = parse_ctest_output(output) or {"failed": 1}
                confidence = compute_confidence(parsed) or {"status": "retry"}

                send_step("test_result", {
                    "parsed": parsed,
                    "confidence": confidence
                })

                if parsed.get("failed", 0) > 0:
                    send_log(logs, parsed.get("summary"))

                # ✅ SUCCESS
                if confidence.get("status") == "success":
                    send_log(logs, "✅ All tests passed")
                    trace.end(output="success")
                    langfuse.flush()
                    return {"status": "success", "logs": logs}

                send_log(logs, "🔧 Debugging...")

                # =========================
                # DEBUG
                # =========================
                fix_result = fix_code(
                    parsed.get("summary", output),
                    files,
                    trace=trace
                )

                if not isinstance(fix_result, dict):
                    send_log(logs, f"🚨 Debug agent returned invalid result: {type(fix_result)}")
                    continue

                updated_files = fix_result.get("files")

                # 🔥 DEBUG VISIBILITY (CRITICAL)
                send_log(logs, f"DEBUG RAW TYPE: {type(updated_files)}")
                send_log(logs, f"DEBUG RAW VALUE: {str(updated_files)[:300]}")

                # 🔥 FIX: Prevent skip due to invalid type
                if not isinstance(updated_files, list):
                    send_log(logs, "⚠️ Invalid debug output → using previous files")
                    updated_files = files

                # 🔥 FIX: Prevent skip due to empty output
                if not updated_files:
                    send_log(logs, "⚠️ Empty debug output → using previous files")
                    updated_files = files

                send_log(logs, f"DEBUG: Raw debug files count = {len(updated_files)}")

                # =========================
                # NORMALIZATION
                # =========================
                normalized_files = []

                for f in updated_files:
                    if isinstance(f, dict):
                        filename = f.get("filename")
                        content = f.get("content")

                        if isinstance(filename, str) and filename.strip() and isinstance(content, str):
                            normalized_files.append({
                                "filename": filename.strip(),
                                "content": content
                            })

                send_log(logs, f"DEBUG: Normalized files count = {len(normalized_files)}")

                if not normalized_files:
                    send_log(logs, "⚠️ No valid normalized files → fallback to previous")
                    normalized_files = files

                # =========================
                # 🔥 SINGLE WRITE (GUARANTEED)
                # =========================
                send_log(logs, f"🔥 WRITING {len(normalized_files)} FILES")

                write_result = write_files(normalized_files)

                send_log(logs, f"🔥 WRITE RESULT → {write_result}")

                if not write_result.get("success"):
                    send_log(logs, f"⚠️ Write failed: {write_result.get('error')}")
                    continue

                files = normalized_files

                send_log(logs, f"✅ Fix applied ({write_result.get('count')} files)")

            except Exception as loop_error:
                send_log(logs, f"🚨 Attempt {attempt} crashed: {loop_error}")
                continue

        trace.end(level="ERROR", status_message="Max retries exceeded")
        langfuse.flush()

        return {"status": "error", "logs": logs}

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
