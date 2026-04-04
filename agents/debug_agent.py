from services.llm_service import llm
import json


def fix_code(error_log, files, trace=None, parent_span=None):

    # SAFE span creation
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

🔧 ALSO RETURN DEBUG SUMMARY:
- root_cause: what caused the failure
- fix: what changes you made

Return ONLY valid JSON.

STRICT RULES:
- "files" MUST be a list
- Each item MUST contain:
    - "filename": non-empty string with extension (.cpp/.h)
    - "content": non-empty string
- DO NOT return empty filename
- DO NOT omit filename
- DO NOT return null values
- DO NOT return raw strings

If fixing existing files:
- Preserve SAME filenames
- ONLY modify content

Example:
{
  "files": [
    {"filename": "aeb_controller.cpp", "content": "...fixed code..."},
    {"filename": "aeb_controller.h", "content": "..."}
  ],
  "debug_summary": {
    "root_cause": "...",
    "fix": "..."
  }
}
"""

    generation = None
    text = None

    try:
        # CREATE GENERATION (Langfuse)
        if span:
            generation = span.generation(
                name="llm_fix_code",
                model="gpt-4o",
                input=prompt,
                metadata={"agent": "debug_agent"}
            )

        response = llm.invoke(prompt)
        text = response.content.strip()

        # END GENERATION (raw output)
        if generation:
            generation.end(
                output=text[:2000]
            )

        # Clean response
        cleaned = text.replace("```json", "").replace("```", "")

        parsed = json.loads(cleaned)

        updated_files = parsed.get("files", [])

        # Extract debug summary safely
        debug_summary = parsed.get("debug_summary", {
            "root_cause": "Not provided",
            "fix": "Not provided"
        })

        # End span with structured output
        if span:
            span.end(
                output={
                    "files_updated": len(updated_files),
                    "root_cause": debug_summary.get("root_cause"),
                    "fix": debug_summary.get("fix")
                }
            )

        return {
            "files": updated_files,
            "debug_summary": debug_summary
        }

    except Exception as e:

        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": text[:2000] if text else "no response"
                }
            )

        if span:
            span.end(
                level="ERROR",
                status_message=str(e)
            )

        raise ValueError(
            f"Debug agent failed to return valid JSON:\n{text if text else 'No response'}"
        )
