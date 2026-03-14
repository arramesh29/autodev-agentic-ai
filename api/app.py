from fastapi import FastAPI
from workflows.development_workflow import run_workflow

app = FastAPI()

@app.post("/generate")

def generate(requirement: str):

    result = run_workflow(requirement)

    return {"code": result}
