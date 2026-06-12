from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import uuid
import os

from api.file_api import router as file_router

from agents.requirements_analysis_agent import analyze_requirements
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code
from agents.conflict_resolution_agent import resolve_conflicts_llm
from agents.ambiguity_resolution_agent import resolve_ambiguities_llm

from tools.requirements_validator import validate_requirements
from tools.user_decision_handler import apply_user_choices
from tools.test_parser import parse_ctest_output
from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake
from tools.build_tool import build_and_test
from tools.human_loop import handle_user_input
from tools.confidence_scorer import compute_confidence
from tools.requirements_output_writer import write_requirements_output
from tools.metrics_collector import generate_execution_metrics

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(file_router)

SESSION_STORE = {}


def sse(data):
    return f"data: {json.dumps(data)}\n\n"


# =========================================================
# 🔥 NEW: SAVE REQUIREMENTS ONLY ONCE
# =========================================================
def save_requirements_once(session_id, requirements, send):

    session = SESSION_STORE.get(session_id, {})

    # 🔥 prevent duplicate save during debug/codegen retries
    if session.get("requirements_saved"):
        return None

    output_payload = {
        "metadata": {
            "session_id": session_id,
            "source": "user_input"
        },
        "input_requirements": session.get("input"),
        "analyzed_requirements": session.get("analysis", {}).get("requirements", []),
        "conflicts": session.get("conflicts", []),
        "ambiguities": session.get("ambiguities", []),
        "final_requirements": requirements
    }

    file_path = write_requirements_output(session_id, output_payload)

    SESSION_STORE[session_id]["requirements_saved"] = True

    print("📁 Requirements saved at:", file_path)

    return send({
        "step": "requirements_saved",
        "file": file_path
    })

def emit_metrics(
    session_id,
    status,
    send
):

    try:

        req_file = None

        generated_dir = "generated"

        if os.path.exists(generated_dir):

            for f in os.listdir(generated_dir):

                if (
                    f.startswith("requirements_")
                    and session_id in f
                ):
                    req_file = os.path.join(
                        generated_dir,
                        f
                    )
                    break

        metrics = generate_execution_metrics(
            session_id=session_id,
            pipeline_status=status,
            requirements_file=req_file
        )

        return send({
            "step": "metrics_generated",
            "metrics": metrics
        })

    except Exception as e:

        return send({
            "step": "metrics_generation_failed",
            "message": str(e)
        })

# =========================================================
# 🚀 START PIPELINE
# =========================================================
@app.get("/agent/stream")
def stream_workflow(query: str):

    session_id = str(uuid.uuid4())

    def event_stream():

        def send(data):
            data["session_id"] = session_id
            print("SENDING:", data)
            return sse(data)

        try:

            yield send({"step": "start"})

            # =================================================
            # REQUIREMENTS ANALYSIS
            # =================================================
            analysis = analyze_requirements(query)

            yield send({
                "step": "requirements_analyzed",
                "data": analysis
            })

            validated = validate_requirements(analysis)

            requirements = validated.get("requirements", [])
            conflicts = validated.get("conflicts", [])
            ambiguities = validated.get("ambiguities", [])

            # =================================================
            # SESSION STORE
            # =================================================
            SESSION_STORE[session_id] = {
                "input": query,
                "analysis": analysis,
                "requirements": requirements,
                "conflicts": conflicts,
                "ambiguities": ambiguities,
                "final_requirements": [],
                "requirements_saved": False,
                "stage": "requirements"
            }

            # =================================================
            # CONFLICT RESOLUTION
            # =================================================
            if conflicts:

                yield send({
                    "step": "conflict_detected",
                    "details": conflicts
                })

                resolved = resolve_conflicts_llm(
                    requirements,
                    conflicts
                )

                # ---------------------------------------------
                # USER INPUT REQUIRED
                # ---------------------------------------------
                if resolved.get("needs_user_input"):

                    SESSION_STORE[session_id]["stage"] = "conflict"

                    yield send(
                        handle_user_input(
                            "conflict_resolution",
                            resolved["questions"]
                        )
                    )

                    return

                # ---------------------------------------------
                # AUTO RESOLVED
                # ---------------------------------------------
                resolved_requirements = resolved["resolved_requirements"]
                
                original_map = {
                    r["id"]: r
                    for r in requirements
                }
                
                for r in resolved_requirements:
                
                    original_map[r["id"]] = r
                
                requirements = list(
                    original_map.values()
                )

                SESSION_STORE[session_id]["requirements"] = requirements

                yield send({
                    "step": "conflict_resolved"
                })

            # =================================================
            # AMBIGUITY RESOLUTION
            # =================================================
            if ambiguities:

                SESSION_STORE[session_id]["stage"] = "ambiguity"

                yield send({
                    "step": "ambiguity_detected",
                    "details": ambiguities
                })

                resolved = resolve_ambiguities_llm(
                    requirements,
                    ambiguities
                )

                # ---------------------------------------------
                # AUTO RESOLVED
                # ---------------------------------------------
                if resolved.get("step") == "ambiguity_resolved_auto":

                    resolved_requirements = resolved["requirements"]
                    
                    original_map = {
                        r["id"]: r
                        for r in requirements
                    }
                    
                    for r in resolved_requirements:
                    
                        original_map[r["id"]] = r
                    
                    requirements = list(
                        original_map.values()
                    )

                    SESSION_STORE[session_id]["requirements"] = requirements

                    yield send({
                        "step": "ambiguity_auto_resolved"
                    })

                # ---------------------------------------------
                # USER INPUT REQUIRED
                # ---------------------------------------------
                else:

                    yield send(resolved)

                    return

            # =================================================
            # FINAL REQUIREMENTS
            # =================================================
            SESSION_STORE[session_id]["final_requirements"] = requirements

            # =================================================
            # SAVE REQUIREMENTS ONLY ONCE
            # =================================================
            msg = save_requirements_once(
                session_id,
                requirements,
                send
            )

            if msg:
                yield msg

            # =================================================
            # RUN IMPLEMENTATION PIPELINE
            # =================================================
            yield from run_pipeline(
                session_id,
                requirements,
                send
            )

        except Exception as e:

            try:
            
                yield emit_metrics(
                    session_id,
                    "PIPELINE_EXCEPTION",
                    send
                )
            
            except Exception as e:
            
                print(
                    f"Metrics generation failed: {e}"
                )

            yield send({
                "step": "error",
                "message": str(e)
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


# =========================================================
# 🚀 CONTINUE PIPELINE
# =========================================================
@app.get("/agent/continue")
def continue_pipeline(session_id: str):

    session = SESSION_STORE.get(session_id, {})

    requirements = session.get("requirements", [])

    def event_stream():

        def send(data):
            data["session_id"] = session_id
            print("SENDING:", data)
            return sse(data)

        try:

            # =================================================
            # SAFETY CHECK
            # =================================================
            if not requirements:

                yield send({
                    "step": "blocked",
                    "message": "No resolved requirements available"
                })

                return

            # =================================================
            # FINAL REQUIREMENTS
            # =================================================
            SESSION_STORE[session_id]["final_requirements"] = requirements

            # =================================================
            # SAVE ONLY ONCE
            # =================================================
            msg = save_requirements_once(
                session_id,
                requirements,
                send
            )

            if msg:
                yield msg

            # =================================================
            # CONTINUE IMPLEMENTATION PIPELINE
            # =================================================
            yield from run_pipeline(
                session_id,
                requirements,
                send
            )

        except Exception as e:

            try:
            
                yield emit_metrics(
                    session_id,
                    "PIPELINE_EXCEPTION",
                    send
                )
            
            except Exception as exc:
            
                print(
                    f"Metrics generation failed: {e}"
                )
            
            yield send({
                "step": "error",
                "message": str(e)
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


# =========================================================
# 🔥 IMPLEMENTATION PIPELINE
# =========================================================
def run_pipeline(session_id, requirements, send):

    # =====================================================
    # PLAN
    # =====================================================
    plan = create_plan(requirements)

    yield send({
        "step": "plan_created"
    })

    # =====================================================
    # CODEGEN
    # =====================================================
    MAX_CODEGEN_RETRIES = 2

    result = None

    for retry in range(MAX_CODEGEN_RETRIES):

        result = generate_code(
            plan,
            requirements=requirements
        )

        if not result.get("error"):
            break

        yield send({
            "step": "codegen_retry",
            "attempt": retry + 1,
            "message": result.get("error")
        })

    # =====================================================
    # CODEGEN FAILURE
    # =====================================================
    if result.get("error"):

        yield send({
            "step": "codegen_error",
            "message": result["error"],
            "raw": result.get("raw_output", "")[:500]
        })
        
        try:
        
            yield emit_metrics(
                session_id,
                "CODEGEN_FAILED",
                send
            )
        
        except Exception as e:
        
            print(
                f"Metrics generation failed: {e}"
            )
        
        return

    files = result.get("files", [])

    yield send({
        "step": "code_generated",
        "files": [f["filename"] for f in files]
    })

    # =====================================================
    # WRITE FILES
    # =====================================================
    write_files(files)

    generate_cmake(files)

    # =====================================================
    # BUILD + DEBUG LOOP
    # =====================================================
    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):

        yield send({
            "step": "build_attempt",
            "attempt": attempt
        })

        output = build_and_test()

        parsed = parse_ctest_output(output)

        confidence = compute_confidence(parsed)

        yield send({
            "step": "test_result",
            "parsed": parsed,
            "confidence": confidence
        })

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------
        if confidence["status"] == "success":
        
            try:
            
                yield emit_metrics(
                    session_id,
                    "SUCCESS",
                    send
                )
            
            except Exception as e:
            
                print(
                    f"Metrics generation failed: {e}"
                )
        
            yield send({
                "step": "done"
            })
        
            return

        # -------------------------------------------------
        # DEBUG FIX
        # -------------------------------------------------
        fix_result = fix_code(output, files)

        files = fix_result.get("files", files)

        write_files(files)

    # =====================================================
    # FAILED AFTER RETRIES
    # =====================================================
    try:
    
        yield emit_metrics(
            session_id,
            "DEBUG_FAILED",
            send
        )
    
    except Exception as e:
    
        print(
            f"Metrics generation failed: {e}"
        )
    
    yield send({
        "step": "failed"
    })


# =========================================================
# 🔥 RESOLVE CONFLICT
# =========================================================
@app.post("/agent/resolve-conflict")
def resolve_conflict(request: dict):

    session_id = request.get("session_id")

    answers = request.get("answers", [])

    session = SESSION_STORE.get(session_id, {})

    requirements = session.get("requirements", [])

    updated = apply_user_choices(
        requirements,
        answers
    )

    SESSION_STORE[session_id]["requirements"] = updated

    SESSION_STORE[session_id]["conflicts_resolved"] = answers

    return {
        "status": "conflict_resolved"
    }


# =========================================================
# 🔥 RESOLVE AMBIGUITY
# =========================================================
@app.post("/agent/resolve-ambiguity")
def resolve_ambiguity(request: dict):

    session_id = request.get("session_id")

    decisions = request.get("decisions", [])

    session = SESSION_STORE.get(session_id, {})

    requirements = session.get("requirements", [])

    updated = apply_user_choices(
        requirements,
        decisions
    )

    SESSION_STORE[session_id]["requirements"] = updated

    SESSION_STORE[session_id]["ambiguities_resolved"] = decisions

    return {
        "status": "ambiguity_resolved"
    }


# =========================================================
# 🚀 LEGACY API
# =========================================================
@app.post("/agent/run")
def run_agent(request: dict):

    return {
        "status": "use /agent/stream"
    }
