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

    # Create ROOT TRACE
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
        structured_logs.append({
            "step": "planning",
            "status": "success",
            "output": plan
        })

        # =========================
        # ⚙️ STEP 2: CODE GENERATION
        # =========================
        code_span = trace.span(name="code_generation")

        result = generate_code(plan)
        files = result.get("files", [])

        if not files:
            code_span.end(level="ERROR", status_message="No files generated")

            return {
                "status": "error",
                "action": "generate_code",
                "data": None,
                "logs": logs,
                "structured_logs": structured_logs,
                "error": "No files generated"
            }

        code_span.end(output={"file_count": len(files)})

        structured_logs.append({
            "step": "code_generation",
            "status": "success",
            "file_count": len(files)
        })

        # =========================
        # 📁 FILE WRITE
        # =========================
        file_span = trace.span(name="file_write")

        write_files(files)

        file_span.end()

        logs.append("📁 Files written")

        # =========================
        # ⚙️ CMAKE GENERATION
        # =========================
        cmake_span = trace.span(name="cmake_generation")

        generate_cmake(files)

        cmake_span.end()

        logs.append("⚙️ CMake generated")

        MAX_RETRIES = 5

        # =========================
        # 🔁 DEBUG LOOP
        # =========================
        debug_loop_span = trace.span(name="debug_loop")

        for attempt in range(MAX_RETRIES):

            attempt_span = debug_loop_span.span(
                name=f"attempt_{attempt}",
                metadata={"attempt": attempt}
            )

            logs.append(f"\n=== Attempt {attempt} ===")

            structured_logs.append({
                "step": "attempt",
                "attempt_number": attempt
            })

            # =========================
            # 🏗️ BUILD + TEST
            # =========================
            build_span = attempt_span.span(name="build_and_test")

            output = build_and_test()

            build_span.end(output=output)

            # =========================
            # 📊 TEST ANALYSIS
            # =========================
            analysis_span = attempt_span.span(name="test_analysis")

            parsed = parse_ctest_output(output)
            confidence = compute_confidence(parsed)

            analysis_span.end(
                output={
                    "parsed": parsed,
                    "confidence": confidence
                }
            )

            logs.append(f"📊 Test Summary: {parsed}")
            logs.append(f"📈 Confidence Score: {confidence['confidence_score']}")

            structured_logs.append({
                "step": "test_analysis",
                "parsed": parsed,
                "confidence": confidence
            })

            # =========================
            # ✅ SUCCESS
            # =========================
            if confidence["status"] == "success":

                attempt_span.end(output="success")
                debug_loop_span.end()

                logs.append("✅ All tests passed with high confidence")

                trace.end(output="success")

                return {
                    "status": "success",
                    "action": "autodev_workflow",
                    "data": {
                        "summary": "Code generated, tested, and validated successfully",
                        "generated_files": [
                            {
                                "name": f["filename"],
                                "type": f["filename"].split(".")[-1]
                            }
                            for f in files if "filename" in f
                        ],
                        "test_summary": parsed,
                        "confidence": confidence,
                        "attempts": attempt + 1
                    },
                    "logs": logs,
                    "structured_logs": structured_logs,
                    "error": None
                }

            # =========================
            # ❌ FAILURE ANALYSIS
            # =========================
            if confidence["status"] == "no_tests":
                reason = "No Tests Executed"
            else:
                if "error c" in output.lower() or "nmake" in output.lower():
                    reason = "Compilation/Build Error"
                elif parsed["failed"] > 0:
                    reason = "Test Failure (Logic Error)"
                else:
                    reason = "Unknown Issue"

            logs.append(f"🔍 Reason: {reason}")

            structured_logs.append({
                "step": "failure_analysis",
                "reason": reason
            })

            # =========================
            # 🔧 DEBUG FIX
            # =========================
            debug_span = attempt_span.span(name="debug_fix")

            try:
                files = fix_code(
                                    output,
                                    files,
                                    trace=trace,
                                    parent_span=debug_span
                                )
                write_files(files)

                debug_span.end(output="fix_applied")

                logs.append("✅ Fix applied")

                structured_logs.append({
                    "step": "debug",
                    "status": "fix_applied"
                })

            except Exception as e:
                debug_span.end(level="ERROR", status_message=str(e))

                return {
                    "status": "error",
                    "action": "debug_code",
                    "data": {
                        "summary": "Debug agent failed",
                        "generated_files": [f["filename"] for f in files]
                    },
                    "logs": logs,
                    "structured_logs": structured_logs,
                    "error": str(e)
                }

            attempt_span.end()

        debug_loop_span.end()

        # =========================
        # ❌ FINAL FAILURE
        # =========================
        trace.end(level="ERROR", status_message="Max retries exceeded")

        return {
            "status": "error",
            "action": "autodev_workflow",
            "data": {
                "summary": "Failed after max retries",
                "generated_files": [f["filename"] for f in files],
                "attempts": MAX_RETRIES
            },
            "logs": logs,
            "structured_logs": structured_logs,
            "error": "Max retries exceeded"
        }

    except Exception as e:
        trace.end(level="ERROR", status_message=str(e))
        raise
