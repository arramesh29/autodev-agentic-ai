from fastapi import FastAPI
from workflows.development_workflow import run_workflow
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from api.file_api import router as file_router

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
