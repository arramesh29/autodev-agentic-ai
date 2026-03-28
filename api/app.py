from fastapi import FastAPI
from workflows.development_workflow import run_workflow
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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

class RequirementRequest(BaseModel):
    requirement: str

@app.post("/agent/run")
def run_agent(request: AgentRequest):
    return run_workflow(request.query)
