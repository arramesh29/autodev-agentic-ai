from fastapi import FastAPI
from workflows.development_workflow import run_workflow
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Autodev Agentic AI API running"}

class RequirementRequest(BaseModel):
    requirement: str

@app.post("/generate")
def generate(req: RequirementRequest):
    return {"result": run_workflow(req.requirement)}
