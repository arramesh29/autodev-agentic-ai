from services.llm_service import llm
import json


def fix_code(error_log, files, trace=None, parent_span=None):

    # Create span for debug agent
    span = None
    if trace:
        span = (
            parent_span.span(name="fix_code_agent")
            if parent_span
            else trace.span(name="fix_code_agent")
        )

    prompt = f"""
You are a senior automotive C++ software engineer.

The system failed during build or test execution.

ERROR / TEST OUTPUT:
{error_log}

FILES:
{files}

Instructions:
- Fix compilation errors if present
- Fix failing test logic if present
- Do NOT hardcode values just to pass tests
- Maintain clean, production-quality C++ code
- Ensure proper includes and correct formulas

Return ONLY valid JSON:
{{
  "files":[{{"filename":"...","content":"..."}}]
}}
"""

    try:
        # Attach LLM call to Langfuse trace
        response = llm.invoke(
            prompt,
            metadata={
                "langfuse_trace_id": trace.id if trace else None,
                "langfuse_parent_observation_id": span.id if span else None,
                "agent": "debug_agent"
            }
        )

        text = response.content.strip()

        # Clean response
        text = text.replace("```json", "").replace("```", "")

        parsed = json.loads(text)

        updated_files = parsed.get("files", [])

        # End span with useful output
        if span:
            span.end(
                output={
                    "files_updated": len(updated_files),
                    "error_log_summary": error_log[:500]  # truncate for UI
                }
            )

        return updated_files

    except Exception as e:
        # Proper error tracking
        if span:
            span.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": text if "text" in locals() else "no response"
                }
            )

        raise ValueError(
            f"Debug agent failed to return valid JSON:\n{text if 'text' in locals() else 'No response'}"
        )
