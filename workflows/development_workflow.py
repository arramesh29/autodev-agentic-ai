import json
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


# 🔥 Recursive extractor
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

        plan = create_plan(
            requirement,
            trace=trace,
            parent_span=plan_span
        )

        plan_span.end(output=plan)
        logs.append("📋 Plan created")

        # =========================
        # ⚙️ CODE GEN
        # =========================
        code_span = trace.span(name="code_generation")

        result = generate_code(plan)

        if not isinstance(result, dict):
            raise ValueError("generate_code returned invalid format")

        files = extract_files_recursively(result.get("files", []))

        if not files:
            raise ValueError("No valid files from generate_code")

        code_span.end(output={"file_count": len(files)})

        # 🔥 SAFE INITIAL WRITE (FIX 3)
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
                logs.append(f"🔥 LOOP ENTERED attempt {attempt}")

                # -------------------------
                # BUILD + TEST
                # -------------------------
                output = build_and_test()

                parsed = parse_ctest_output(output)
                if not isinstance(parsed, dict):
                    parsed = {"failed": 1, "summary": "Invalid parser"}

                confidence = compute_confidence(parsed)
                if not isinstance(confidence, dict):
                    confidence = {"confidence_score": 0, "status": "retry"}

                logs.append(f"📊 Test Summary: {parsed}")
                logs.append(f"📈 Confidence Score: {confidence.get('confidence_score')}")

                if parsed.get("failed", 0) > 0:
                    logs.append("\n❌ FAILURE DETAILS")
                    logs.append(parsed.get("summary"))

                # -------------------------
                # SUCCESS EXIT
                # -------------------------
                if confidence.get("status") == "success":
                    logs.append("✅ All tests passed")

                    trace.end(output="success")
                    langfuse.flush()

                    return {"status": "success", "logs": logs}

                logs.append("🔧 Debugging...")

                # -------------------------
                # DEBUG STEP
                # -------------------------
                fix_result = fix_code(
                    parsed.get("summary", output),
                    files,
                    trace=trace
                )

                # -------------------------
                # EXTRACT FILES
                # -------------------------
                updated_files = extract_files_recursively(fix_result)

                if not updated_files:
                    logs.append("⚠️ No valid debug files extracted")
                    continue

                # -------------------------
                # NORMALIZE FILES
                # -------------------------
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

                # 🔥 SAFE WRITE (FIX 2)
                write_result = write_files(normalized_files)

                if not write_result.get("success"):
                    logs.append(f"⚠️ Write failed: {write_result.get('error')}")
                    continue

                files = normalized_files
                logs.append("✅ Fix applied")

            except Exception as loop_error:
                logs.append(f"🚨 Attempt {attempt} crashed: {loop_error}")
                continue

        # =========================
        # ❌ MAX RETRIES
        # =========================
        trace.end(level="ERROR", status_message="Max retries exceeded")
        langfuse.flush()

        return {"status": "error", "logs": logs}

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
