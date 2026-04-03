from services.llm_service import llm
import json


def generate_code(spec, trace=None, parent_span=None):

    # Create span for this agent
    span = None
    if trace:
        span = (
            parent_span.span(name="generate_code_agent")
            if parent_span
            else trace.span(name="generate_code_agent")
        )

    prompt = f"""
    You are an automotive C++ software engineer.
    Generate production-grade C++ code and unit tests using GoogleTest.

    Requirements:
    - Follow modular design (.h + .cpp)
    - No experimental code
    - Deterministic logic (no randomness)
    - Automotive safety style (clear logic, no undefined behavior)

    IMPORTANT:
        - Include all necessary headers
        - Use standard C++ includes
        - Ensure code compiles without errors
        - Avoid missing includes (e.g., <limits>, <cmath>, <vector>)

    Unit Test Requirements:
    - Use GoogleTest
    - Cover:
      - C0 (statement coverage)
      - C1 (branch coverage)
    - Include:
      - normal cases
      - boundary conditions
      - failure conditions
      - edge cases

    Return ONLY valid JSON.
    Do not include explanations.
    Do not include markdown.

    Format:

    {{
      "files":[
        {{"filename":"aeb_controller.h","content":"header code"}},
        {{"filename":"aeb_controller.cpp","content":"implementation"}},
        {{"filename":"test_aeb_controller.cpp","content":"GoogleTest code"}}
      ]
    }}

    Requirement:
    {spec}
    """

    try:
        # Attach LLM call to Langfuse trace
        response = llm.invoke(
            prompt,
            metadata={
                "langfuse_trace_id": trace.id if trace else None,
                "langfuse_parent_observation_id": span.id if span else None,
                "agent": "code_generation"
            }
        )

        text = response.content.strip()

        # Clean response
        text = text.replace("```json", "")
        text = text.replace("```", "")

        result = json.loads(text)

        # End span with output
        if span:
            span.end(
                output={
                    "file_count": len(result.get("files", []))
                }
            )

        return result

    except Exception as e:
        # Capture errors in Langfuse
        if span:
            span.end(
                level="ERROR",
                status_message=str(e)
            )

        raise ValueError(f"Invalid JSON from LLM:\n{text if 'text' in locals() else 'No response'}")
