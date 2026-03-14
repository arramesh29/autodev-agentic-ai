from agents.planner_agent import create_plan
from agents.code_generation_agent import generate_code
from tools.static_analysis_tool import run_static_analysis
from services.langfuse_service import langfuse


def run_workflow(requirement):

    trace = langfuse.start_trace(name="automotive-development")

    plan = create_plan(requirement)

    code = generate_code(plan)

    trace.end()

    return code
