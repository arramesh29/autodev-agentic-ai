from workflows.development_workflow import run_workflow

requirement = """
Design a braking controller module.
Input: wheel speed
Output: brake pressure
"""

result = run_workflow(requirement)

print(result)
