from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import uuid

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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(file_router)

# 🔥 SESSION STORE
SESSION_STORE = {}


def sse(data):
    return f"data: {json.dumps(data)}\n\n"


# 🚀 START PIPELINE
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

            analysis = analyze_requirements(query)
            yield send({"step": "requirements_analyzed", "data": analysis})

            validated = validate_requirements(analysis)

            requirements = validated.get("requirements", [])
            conflicts = validated.get("conflicts", [])
            ambiguities = validated.get("ambiguities", [])

            SESSION_STORE[session_id] = {
                "requirements": requirements
            }

            # 🔥 CONFLICT
            if conflicts:
                yield send({"step": "conflict_detected", "details": conflicts})

                resolved = resolve_conflicts_llm(requirements, conflicts)

                if resolved.get("needs_user_input"):
                    SESSION_STORE[session_id]["stage"] = "conflict"
                    yield send(handle_user_input("conflict_resolution", resolved["questions"]))
                    return

                requirements = resolved["resolved_requirements"]
                SESSION_STORE[session_id]["requirements"] = requirements

                yield send({"step": "conflict_resolved"})

            # 🔥 AMBIGUITY
            if ambiguities:
                SESSION_STORE[session_id]["stage"] = "ambiguity"

                yield send({"step": "ambiguity_detected", "details": ambiguities})

                resolved = resolve_ambiguities_llm(requirements, ambiguities)

                yield send(resolved)
                return

            # 🚀 CONTINUE
            yield from run_pipeline(session_id, requirements, send)

        except Exception as e:
            yield send({"step": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🚀 CONTINUE PIPELINE (🔥 NEW)
@app.get("/agent/continue")
def continue_pipeline(session_id: str):

    session = SESSION_STORE.get(session_id, {})
    requirements = session.get("requirements", [])

    def event_stream():

        def send(data):
            data["session_id"] = session_id
            return sse(data)

        yield from run_pipeline(session_id, requirements, send)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🔥 PIPELINE WITH DEBUG LOOP
def run_pipeline(session_id, requirements, send):

    plan = create_plan(requirements)
    yield send({"step": "plan_created"})

    result = generate_code(plan, requirements=requirements)

    if result.get("error"):
        yield send({"step": "codegen_error", "message": result["error"]})
        return

    files = result.get("files", [])

    yield send({
        "step": "code_generated",
        "files": [f["filename"] for f in files]
    })

    write_files(files)
    generate_cmake(files)

    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):

        yield send({"step": "build_attempt", "attempt": attempt})

        output = build_and_test()

        parsed = parse_ctest_output(output)
        confidence = compute_confidence(parsed)

        yield send({
            "step": "test_result",
            "parsed": parsed,
            "confidence": confidence
        })

        if confidence["status"] == "success":
            yield send({"step": "done"})
            return

        fix_result = fix_code(output, files)
        files = fix_result.get("files", files)
        write_files(files)

    yield send({"step": "failed"})


# 🔥 RESOLVE CONFLICT (UPDATED)
@app.post("/agent/resolve-conflict")
def resolve_conflict(request: dict):

    session_id = request.get("session_id")
    answers = request.get("answers", [])

    session = SESSION_STORE.get(session_id, {})
    requirements = session.get("requirements", [])

    updated = apply_user_choices(requirements, answers)

    SESSION_STORE[session_id]["requirements"] = updated

    return {"status": "conflict_resolved"}


# 🔥 RESOLVE AMBIGUITY (UPDATED)
@app.post("/agent/resolve-ambiguity")
def resolve_ambiguity(request: dict):

    session_id = request.get("session_id")
    decisions = request.get("decisions", [])

    session = SESSION_STORE.get(session_id, {})
    requirements = session.get("requirements", [])

    updated = apply_user_choices(requirements, decisions)

    SESSION_STORE[session_id]["requirements"] = updated

    return {"status": "ambiguity_resolved"}


@app.post("/agent/run")
def run_agent(request: dict):
    return {"status": "use /agent/stream"}
