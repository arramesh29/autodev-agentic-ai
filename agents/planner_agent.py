from services.llm_service import llm


def create_plan(requirement, trace=None, parent_span=None):

    # Create span for planner agent
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

    try:
        # Attach LLM call to Langfuse trace
        response = llm.invoke(
            prompt,
            config={
                "metadata": {
                    "langfuse_trace_id": trace.id if trace else None,
                    "langfuse_parent_observation_id": span.id if span else None,
                    "agent": "planner_agent"
                }
            }
        )

        output = response.content

        # End span with output
        if span:
            span.end(output=output[:1000])  # truncate for UI

        return output

    except Exception as e:
        # Proper error tracking
        if span:
            span.end(
                level="ERROR",
                status_message=str(e)
            )
        raise
