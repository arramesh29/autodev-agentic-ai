from langfuse import observe
from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code

@observe()
def run_workflow(requirement):

    plan = create_plan(requirement)

    code = generate_code(plan)

    return code
