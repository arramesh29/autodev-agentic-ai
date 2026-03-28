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
        import time
        import json
    
        def send(msg):
            print("SENDING:", msg)
            return f"data: {json.dumps(msg)}\n\n"
    
        yield send({"step": "start"})
        time.sleep(0.5)   # 🔥 REQUIRED
    
        yield send({"step": "middle"})
        time.sleep(0.5)
    
        yield send({"step": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


# 🚀 OPTIONAL: Keep existing batch API (if you have)
@app.post("/agent/run")
def run_agent(request: dict):
    query = request.get("query", "")

    # You can call your existing run_workflow here if needed
    return {"status": "use /agent/stream for live execution"}
