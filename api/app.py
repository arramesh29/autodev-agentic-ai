from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import time

# 🔧 Import your routers
from api.file_api import router as file_router

# 🔧 Import your agents + tools
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code

from tools.file_writer import write_files
from tools.cmake_generator import generate_cmake
from tools.build_tool import build_and_test

from tools.test_parser import parse_ctest_output
from tools.confidence_scorer import compute_confidence


# 🚀 Create app
app = FastAPI()

# 🌐 Enable CORS (IMPORTANT for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📂 Include file API
app.include_router(file_router)


# 🔥 Helper to format SSE messages
def sse(data):
    return f"data: {json.dumps(data)}\n\n"


# 🚀 STREAMING ENDPOINT
@app.get("/agent/stream")
def stream_workflow(query: str):

    def event_stream():

        try:
            # ✅ Start immediately
            yield sse({"step": "start"})
            time.sleep(0.1)

            # 🧠 PLAN
            plan = create_plan(query)
            yield sse({"step": "plan_created"})
            time.sleep(0.1)

            # 🧠 CODE GENERATION
            result = generate_code(plan)
            files = result.get("files", [])

            yield sse({
                "step": "code_generated",
                "files": [f["filename"] for f in files]
            })
            time.sleep(0.1)

            # 💾 WRITE FILES
            write_files(files)
            generate_cmake(files)

            MAX_RETRIES = 5

            # 🔁 BUILD LOOP
            for attempt in range(MAX_RETRIES):

                yield sse({
                    "step": "build_attempt",
                    "attempt": attempt
                })
                time.sleep(0.1)

                output = build_and_test()

                parsed = parse_ctest_output(output)
                confidence = compute_confidence(parsed)

                yield sse({
                    "step": "test_result",
                    "parsed": parsed,
                    "confidence": confidence
                })
                time.sleep(0.1)

                # ✅ SUCCESS
                if confidence["status"] == "success":
                    yield sse({"step": "done"})
                    return

                # 🔧 DEBUG FIX
                files = fix_code(output, files)
                write_files(files)

            # ❌ FAILURE
            yield sse({"step": "failed"})

        except Exception as e:
            # 🔥 IMPORTANT: Send error to frontend
            yield sse({
                "step": "error",
                "message": str(e)
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


# 🚀 OPTIONAL: Keep existing batch API (if you have)
@app.post("/agent/run")
def run_agent(request: dict):
    query = request.get("query", "")

    # You can call your existing run_workflow here if needed
    return {"status": "use /agent/stream for live execution"}
