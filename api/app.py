from fastapi import FastAPI
from workflows.development_workflow import run_workflow
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from api.file_api import router as file_router
from fastapi.responses import StreamingResponse
import json
import time
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code

from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake
from tools.build_tool import build_and_test

from tools.test_parser import parse_ctest_output
from tools.confidence_scorer import compute_confidence

app = FastAPI()
app.include_router(file_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Autodev Agentic AI API running"}

# ✅ REQUEST SCHEMA
class AgentRequest(BaseModel):
    query: str

# ✅ ENDPOINT
@app.post("/agent/run")
def run_agent(request: AgentRequest):
    print("Incoming request:", request)
    return run_workflow(request.query)

@app.get("/agent/stream")
def stream_workflow(query: str):

    def event_stream():

        yield f"data: {json.dumps({'step': 'start'})}\n\n"

        plan = create_plan(query)
        yield f"data: {json.dumps({'step': 'plan_created'})}\n\n"

        result = generate_code(plan)
        files = result.get("files", [])

        yield f"data: {json.dumps({
            'step': 'code_generated',
            'files': [f['filename'] for f in files]
        })}\n\n"

        write_files(files)
        generate_cmake(files)

        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES):

            yield f"data: {json.dumps({
                'step': 'build_attempt',
                'attempt': attempt
            })}\n\n"

            output = build_and_test()

            parsed = parse_ctest_output(output)
            confidence = compute_confidence(parsed)

            yield f"data: {json.dumps({
                'step': 'test_result',
                'parsed': parsed,
                'confidence': confidence
            })}\n\n"

            if confidence["status"] == "success":
                yield f"data: {json.dumps({'step': 'done'})}\n\n"
                return

            files = fix_code(output, files)
            write_files(files)

        yield f"data: {json.dumps({'step': 'failed'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
