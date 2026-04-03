from services.llm_service import llm


def create_plan(requirement, trace=None, parent_span=None):

    # SAFE span creation
    span = None
    if trace:
        span = (
            parent_span.span(name="create_plan_agent")
            if parent_span
            else trace.span(name="create_plan_agent")
        )

    prompt = f"""
    Break the following automotive requirement into
    software development tasks:

    {requirement}
    """

    generation = None
    output = None

    try:
        # CREATE GENERATION (v4 way)
        if span:
            generation = span.generation(
                name="llm_create_plan",
                model="gpt-4o",
                input=prompt,
                metadata={
                    "agent": "planner_agent"
                }
            )

        response = llm.invoke(prompt)

        output = response.content

        # END GENERATION (raw output)
        if generation:
            generation.end(
                output=output[:2000]  # truncate for UI safety
            )

        # End span with structured output
        if span:
            span.end(
                output=output[:1000]
            )

        return output

    except Exception as e:

        # Ensure generation is closed even on failure
        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": output[:2000] if output else "no response"
                }
            )

        if span:
            span.end(
                level="ERROR",
                status_message=str(e)
            )

        raise
