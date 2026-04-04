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

        files = result.get("files", [])

        if isinstance(files, dict):
            files = [files]

        if not isinstance(files, list):
            raise ValueError("files must be list")

        validated_files = []
        for f in files:
            if isinstance(f, dict) and "filename" in f and "content" in f:
                validated_files.append(f)

        if not validated_files:
            raise ValueError("No valid files from generate_code")

        files = validated_files

        code_span.end(output={"file_count": len(files)})

        # 🔥 STRICT WRITE
        try:
            write_files(files)
        except Exception as e:
            logs.append(f"🚨 File write failed: {str(e)}")
            raise

        generate_cmake(files)

        logs.append("📁 Files written")
        logs.append("⚙️ CMake generated")

        # =========================
        # 🔁 LOOP
        # =========================
        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES):

            logs.append(f"\n=== Attempt {attempt} ===")

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

            # ✅ SUCCESS
            if confidence.get("status") == "success":
                logs.append("✅ All tests passed")

                trace.end(output="success")
                langfuse.flush()

                return {"status": "success", "logs": logs}

            logs.append("🔧 Debugging...")

            # =========================
            # 🔧 DEBUG FIX
            # =========================
            try:
                fix_result = fix_code(
                    parsed.get("summary", output),
                    files,
                    trace=trace
                )
            except Exception as e:
                logs.append(f"🚨 Debug agent failed: {str(e)}")
                continue

            # =========================
            # 🔥 ROBUST EXTRACTION (FINAL FIX)
            # =========================

            updated_files = []

            if isinstance(fix_result, dict):

                if "files" in fix_result:
                    updated_files = fix_result["files"]

                elif isinstance(fix_result.get("files"), list):
                    updated_files = fix_result.get("files", [])

                else:
                    logs.append(f"🚨 Invalid fix_result structure: {fix_result}")
                    continue

            else:
                logs.append(f"🚨 Unexpected fix_result type: {type(fix_result)}")
                continue

            # 🔥 FLATTEN NESTED BUG
            flattened_files = []

            for f in updated_files:

                if isinstance(f, dict) and "files" in f:
                    inner_files = f.get("files", [])
                    if isinstance(inner_files, list):
                        flattened_files.extend(inner_files)
                    continue

                flattened_files.append(f)

            # =========================
            # 🔥 STRICT NORMALIZATION
            # =========================

            normalized_files = []

            for f in flattened_files:

                if not isinstance(f, dict):
                    logs.append(f"⚠️ Skipping non-dict file: {f}")
                    continue

                filename = f.get("filename")
                content = f.get("content")

                if not isinstance(filename, str) or not filename.strip():
                    logs.append(f"⚠️ Invalid filename skipped: {f}")
                    continue

                if not isinstance(content, str):
                    logs.append(f"⚠️ Invalid content skipped: {f}")
                    continue

                normalized_files.append({
                    "filename": filename.strip(),
                    "content": content
                })

            if not normalized_files:
                logs.append("⚠️ No valid debug files after flattening, keeping previous")
                continue

            # 🔥 SAFE WRITE
            try:
                write_files(normalized_files)
            except Exception as e:
                logs.append(f"🚨 Fix write failed: {str(e)}")
                logs.append("⚠️ Reverting to previous files")
                continue

            files = normalized_files

            logs.append("✅ Fix applied")

        trace.end(level="ERROR", status_message="Max retries exceeded")
        langfuse.flush()

        return {"status": "error", "logs": logs}

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
