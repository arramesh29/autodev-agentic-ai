from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import time

# 🔧 Import your routers
from api.file_api import router as file_router

# 🔧 Import your agents + tools
from agents.requirements_analysis_agent import analyze_requirements
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from agents.debug_agent import fix_code


from tools.requirements_validator import validate_requirements
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
    
        def send(data):
            print("SENDING:", data)
            return f"data: {json.dumps(data)}\n\n"
    
        try:
            # 🚀 START
            yield send({"step": "start"})
            time.sleep(0.1)
    
            # 🧠 REQUIREMENTS ANALYSIS
            analysis = analyze_requirements(query)
            yield send({
                "step": "requirements_analyzed",
                "data": analysis
            })
            time.sleep(0.1)
    
            # ✅ VALIDATION
            validated = validate_requirements(analysis)
    
            requirements = validated.get("requirements", [])
            conflicts = validated.get("conflicts", [])
            ambiguities = validated.get("ambiguities", [])
    
            # ❌ BLOCK if conflicts
            if conflicts:
                yield send({
                    "step": "error",
                    "type": "conflict",
                    "details": conflicts
                })
                return
    
            # ⚠️ ASK USER if ambiguous
            if ambiguities:
                yield send({
                    "step": "clarification_needed",
                    "details": ambiguities
                })
                return
    
            # ❌ NO VALID REQUIREMENTS
            if not requirements:
                yield send({
                    "step": "error",
                    "message": "No valid requirements extracted"
                })
                return
    
            # 📋 PLAN
            plan = create_plan(requirements)
    
            yield send({
                "step": "plan_created",
                "requirements_count": len(requirements)
            })
            time.sleep(0.1)
    
            # 🧠 CODE GENERATION (FIXED)
            result = generate_code(plan, requirements=requirements)
            files = result.get("files", [])
    
            yield send({
                "step": "code_generated",
                "files": [f["filename"] for f in files]
            })
            time.sleep(0.1)
    
            # 💾 WRITE FILES
            write_files(files)
            generate_cmake(files)
    
            MAX_RETRIES = 5
    
            for attempt in range(MAX_RETRIES):
    
                yield send({
                    "step": "build_attempt",
                    "attempt": attempt
                })
                time.sleep(0.1)
    
                output = build_and_test()
    
                parsed = parse_ctest_output(output)
                confidence = compute_confidence(parsed)
    
                yield send({
                    "step": "test_result",
                    "parsed": parsed,
                    "confidence": confidence
                })
                time.sleep(0.1)
    
                if confidence["status"] == "success":
                    yield send({"step": "done"})
                    return
    
                # 🔧 DEBUG FIX LOOP
                fix_result = fix_code(output, files)
                files = fix_result.get("files", files)
    
                write_files(files)
    
            yield send({"step": "failed"})
    
        except Exception as e:
            yield send({
                "step": "error",
                "message": str(e)
            })
        
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

# 🚀 OPTIONAL: Keep existing batch API (if you have)
@app.post("/agent/run")
def run_agent(request: dict):
    query = request.get("query", "")

    # You can call your existing run_workflow here if needed
    return {"status": "use /agent/stream for live execution"}
