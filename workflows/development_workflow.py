from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code


def run_workflow(requirement):

    print("Planning task...")
    plan = create_plan(requirement)

    print("Generating code...")
    code = generate_code(plan)

    return code
