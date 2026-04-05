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

    try:
        # =========================
        # 🧠 PLAN
        # =========================
        plan_span = trace.span(name="planning")

        plan = create_plan(requirement, trace=trace, parent_span=plan_span)

        plan_span.end(output=plan)
        logs.append("📋 Plan created")

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

            logs.append(f"⚠️ Generation attempt {gen_attempt} missing files: {missing}")

        if not files:
            raise ValueError("❌ Code generation failed")

        code_span.end(output={"file_count": len(files)})

        # INITIAL WRITE
        clean_generated_folder()
        write_result = write_files(files)

        if not write_result.get("success"):
            logs.append(f"⚠️ Initial write failed: {write_result.get('error')}")

        generate_cmake(files)

        logs.append("📁 Files written")
        logs.append("⚙️ CMake generated")

        # =========================
        # 🔁 RETRY LOOP
        # =========================
        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES):

            try:
                logs.append(f"\n=== Attempt {attempt} ===")

                output = build_and_test()

                parsed = parse_ctest_output(output) or {"failed": 1}
                confidence = compute_confidence(parsed) or {"status": "retry"}

                logs.append(f"📊 Test Summary: {parsed}")
                logs.append(f"📈 Confidence Score: {confidence.get('confidence_score')}")

                if parsed.get("failed", 0) > 0:
                    logs.append(parsed.get("summary"))

                # ✅ SUCCESS
                if confidence.get("status") == "success":
                    logs.append("✅ All tests passed")
                    trace.end(output="success")
                    langfuse.flush()
                    return {"status": "success", "logs": logs}

                logs.append("🔧 Debugging...")

                # =========================
                # 🔥 DEBUG FIX (CRITICAL FIX)
                # =========================
                fix_result = fix_code(
                    parsed.get("summary", output),
                    files,
                    trace=trace
                )

                # 🔥 FIX: DIRECT ACCESS (NOT recursive)
                updated_files = fix_result.get("files", [])

                if not isinstance(updated_files, list) or not updated_files:
                    logs.append("⚠️ Debug returned no files")
                    continue

                # 🔥 NORMALIZE
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

                if not normalized_files:
                    logs.append("⚠️ No valid normalized files")
                    continue

                # 🔥 CRITICAL: WRITE UPDATED FILES
                write_result = write_files(normalized_files)

                if not write_result.get("success"):
                    logs.append(f"⚠️ Write failed: {write_result.get('error')}")
                    continue

                files = normalized_files

                logs.append(f"✅ Fix applied ({write_result.get('count')} files)")

            except Exception as loop_error:
                logs.append(f"🚨 Attempt {attempt} crashed: {loop_error}")
                continue

        trace.end(level="ERROR", status_message="Max retries exceeded")
        langfuse.flush()

        return {"status": "error", "logs": logs}

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
