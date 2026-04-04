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
        # ⚙️ CODE GEN (FIXED)
        # =========================
        code_span = trace.span(name="code_generation")

        result = generate_code(plan)

        # 🔥 SAFE ACCESS
        if isinstance(result, dict):
            files = result.get("files", [])
        else:
            logs.append("⚠️ generate_code returned invalid format, using fallback")
            files = []

        # 🔥 NORMALIZE
        if isinstance(files, dict):
            files = [files]

        if not isinstance(files, list):
            logs.append("⚠️ files not list, resetting")
            files = []

        # 🔥 VALIDATE
        validated_files = []
        for f in files:
            if isinstance(f, dict) and "filename" in f and "content" in f:
                validated_files.append(f)

        # 🔥 FALLBACK (CRITICAL)
        if not validated_files:
            logs.append("⚠️ No valid files from generate_code, using fallback")

            validated_files = [
                {
                    "filename": "fallback.cpp",
                    "content": "// fallback\nint main(){return 0;}"
                }
            ]

        files = validated_files

        code_span.end(output={"file_count": len(files)})

        write_files(files)
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

            # =========================
            # ✅ SUCCESS
            # =========================
            if confidence.get("status") == "success":
                logs.append("✅ All tests passed")

                trace.end(output="success")
                langfuse.flush()

                return {"status": "success", "logs": logs}

            logs.append("🔧 Debugging...")

            # =========================
            # 🔧 DEBUG FIX (FINAL VERSION)
            # =========================
            fix_result = fix_code(
                parsed.get("summary", output),
                files,
                trace=trace
            )
            
            logs.append(f"🐞 Debug raw output: {fix_result}")
            
            # SAFE extraction
            updated_files = []
            
            if isinstance(fix_result, dict):
                updated_files = fix_result.get("files", [])
            elif isinstance(fix_result, list):
                updated_files = fix_result
            else:
                logs.append("⚠️ Debug agent returned invalid type")
            
            logs.append(f"📂 Debug files extracted: {updated_files}")
            
            # =========================
            # 🔥 AUTO-REPAIR + NORMALIZE
            # =========================
            normalized_files = []
            
            for idx, f in enumerate(updated_files):
            
                # Case 1: dict
                if isinstance(f, dict):
            
                    filename = f.get("filename")
                    content = f.get("content")
            
                    # 🔥 AUTO-FIX filename
                    if not filename or not isinstance(filename, str) or not filename.strip():
                        logs.append(f"⚠️ Fixing missing filename for item {idx}")
                        filename = f"recovered_{idx}.cpp"
            
                    # 🔥 VALIDATE content
                    if not isinstance(content, str) or not content.strip():
                        logs.append(f"⚠️ Skipping empty content for {filename}")
                        continue
            
                    normalized_files.append({
                        "filename": filename.strip(),
                        "content": content
                    })
            
                # Case 2: raw string (LLM mistake)
                elif isinstance(f, str):
                    logs.append(f"⚠️ Converting raw string to file: recovered_{idx}.cpp")
            
                    normalized_files.append({
                        "filename": f"recovered_{idx}.cpp",
                        "content": f
                    })
            
                else:
                    logs.append(f"⚠️ Unknown file format skipped: {f}")
            
            # =========================
            # 🔥 FINAL FALLBACK
            # =========================
            if not normalized_files:
                logs.append("⚠️ Debug agent failed, keeping previous files")
                normalized_files = files
            
            files = normalized_files
            
            # WRITE UPDATED FILES
            write_files(files)
            
            logs.append("✅ Fix applied")

        trace.end(level="ERROR", status_message="Max retries exceeded")
        langfuse.flush()

        return {"status": "error", "logs": logs}

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
