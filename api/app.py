from fastapi import FastAPI
from workflows.development_workflow import run_workflow

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Autodev Agentic AI API running"}

@app.post("/generate")
def generate(requirement: str):
    return {"result": run_workflow(requirement)}
