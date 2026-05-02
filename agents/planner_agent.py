from services.llm_service import llm


def create_plan(requirements, trace=None, parent_span=None):

    if not requirements:
        raise ValueError("No requirements provided to planner")

    # SAFE span creation
    span = None
    if trace:
        span = (
            parent_span.span(name="create_plan_agent")
            if parent_span
            else trace.span(name="create_plan_agent")
        )

    # 🔧 Format structured requirements
    formatted_requirements = ""
    for r in requirements:
        formatted_requirements += f"{r['id']}: {r['description']}\n"

    # 🧠 Improved prompt
    prompt = f"""
    You are an automotive software architect.

    Convert the following structured requirements into a
    clear software development plan.

    Requirements:
    {formatted_requirements}

    Instructions:
    1. Group requirements into modules
    2. Define:
       - functions
       - interfaces
       - data flow
    3. Ensure traceability:
       - Map each module/function to REQ-ID
    4. Identify test scenarios per requirement

    Output format:

    Module: <name>
    - REQ-IDs: [...]
    - Functions:
    - Inputs/Outputs:
    - Test Cases:
    """

    generation = None
    output = None

    try:
        if span:
            generation = span.generation(
                name="llm_create_plan",
                model="gpt-4o",
                input=prompt,
                metadata={"agent": "planner_agent"}
            )

        response = llm.invoke(prompt)
        output = response.content

        if generation:
            generation.end(output=output[:2000])

        if span:
            span.end(output=output[:1000])

        return output

    except Exception as e:

        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": output[:2000] if output else "no response"
                }
            )

        if span:
            span.end(level="ERROR", status_message=str(e))

        raise
