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


# Create SINGLE Langfuse client
langfuse = Langfuse()


def run_workflow(requirement):

    trace = langfuse.trace(
        name="autodev_workflow",
        input={"requirement": requirement},
        metadata={"system": "agentic-ai-dev"}
    )

    logs = []
    structured_logs = []

    try:
        # =========================
        # 🧠 STEP 1: PLANNING
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
        # ⚙️ STEP 2: CODE GENERATION
        # =========================
        code_span = trace.span(name="code_generation")

        result = generate_code(plan)
        files = result.get("files", [])

        if not files:
            code_span.end(level="ERROR", status_message="No files generated")
            langfuse.flush()

            return {
                "status": "error",
                "error": "No files generated",
                "logs": logs
            }

        code_span.end(output={"file_count": len(files)})

        write_files(files)
        generate_cmake(files)

        logs.append("📁 Files written")
        logs.append("⚙️ CMake generated")

        MAX_RETRIES = 5

        debug_loop_span = trace.span(name="debug_loop")

        for attempt in range(MAX_RETRIES):

            attempt_span = debug_loop_span.span(
                name=f"attempt_{attempt}",
                metadata={"attempt": attempt}
            )

            logs.append(f"\n=== Attempt {attempt} ===")

            # =========================
            # 🏗️ BUILD + TEST
            # =========================
            output = build_and_test()

            parsed = parse_ctest_output(output)
            confidence = compute_confidence(parsed)

            logs.append(f"📊 Test Summary: {parsed}")
            if isinstance(confidence, dict):
                confidence_score = confidence.get("confidence_score", "N/A")
                confidence_status = confidence.get("status", "unknown")
            else:
                confidence_score = "N/A"
                confidence_status = "unknown"
                logs.append("⚠️ Confidence returned invalid format")
            
            logs.append(f"📈 Confidence Score: {confidence_score}")

            # 🔥 FAILURE DETAILS
            if parsed.get("failed", 0) > 0:
                logs.append("\n❌ FAILURE DETAILS")
                logs.append(parsed.get("summary", "No detailed summary available"))

            # =========================
            # ✅ SUCCESS
            # =========================
            if isinstance(confidence, dict) and confidence.get("status") == "success":
                logs.append("✅ All tests passed")

                trace.end(output="success")
                langfuse.flush()

                return {
                    "status": "success",
                    "logs": logs
                }

            # =========================
            # 🔍 FAILURE REASON
            # =========================
            if parsed["failed"] > 0:
                reason = "Test Failure"
            else:
                reason = "Build Error"

            logs.append(f"🔍 Reason: {reason}")

            # =========================
            # 🔧 DEBUG FIX (FIXED SECTION)
            # =========================
            debug_span = attempt_span.span(name="debug_fix")

            try:
                fix_result = fix_code(
                    parsed.get("summary", output),
                    files,
                    trace=trace,
                    parent_span=debug_span
                )

                # 🔥 CRITICAL FIX: SAFE TYPE HANDLING
                if isinstance(fix_result, dict):
                    updated_files = fix_result.get("files", [])
                    debug_summary = fix_result.get("debug_summary", {})

                elif isinstance(fix_result, list):
                    updated_files = fix_result
                    debug_summary = {
                        "root_cause": "Not provided",
                        "fix": "Not provided"
                    }

                else:
                    raise ValueError(f"Unexpected fix_code return type: {type(fix_result)}")

                # 🔥 EXTRA SAFETY
                if not isinstance(updated_files, list):
                    raise ValueError("updated_files must be a list")

                # 🔧 LOG DEBUG ACTION
                logs.append("\n🔧 DEBUG ACTION")
                logs.append(f"Root Cause: {debug_summary.get('root_cause')}")
                logs.append(f"Fix Applied: {debug_summary.get('fix')}")

                # 🔄 APPLY FIX
                files = updated_files
                write_files(files)

                debug_span.end(output="fix_applied")

                logs.append("✅ Fix applied")

            except Exception as e:

                debug_span.end(level="ERROR", status_message=str(e))
                langfuse.flush()

                logs.append(f"❌ Debug Error: {str(e)}")

                return {
                    "status": "error",
                    "error": str(e),
                    "logs": logs
                }

            attempt_span.end()

        # =========================
        # ❌ FINAL FAILURE
        # =========================
        trace.end(level="ERROR", status_message="Max retries exceeded")
        langfuse.flush()

        return {
            "status": "error",
            "error": "Max retries exceeded",
            "logs": logs
        }

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
