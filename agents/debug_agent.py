from services.llm_service import llm
import json
import re


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

Return ONLY valid JSON:
{{
  "files":[{{"filename":"...","content":"..."}}],
  "debug_summary": {{
      "root_cause": "...",
      "fix": "..."
  }}
}}
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

        if generation:
            generation.end(output=text[:2000])

        # =========================
        # 🔥 SAFE JSON EXTRACTION
        # =========================
        cleaned = text.replace("```json", "").replace("```", "")

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in debug agent output")

        json_str = match.group(0)
        parsed = json.loads(json_str)

        # =========================
        # 🔥 VALIDATION (CRITICAL)
        # =========================
        updated_files = parsed.get("files", [])

        if isinstance(updated_files, dict):
            updated_files = [updated_files]

        if not isinstance(updated_files, list):
            raise ValueError("files must be a list")

        validated_files = []

        for f in updated_files:
            if not isinstance(f, dict):
                continue

            filename = f.get("filename")
            content = f.get("content")

            if isinstance(filename, str) and filename.strip() and isinstance(content, str):
                validated_files.append({
                    "filename": filename.strip(),
                    "content": content
                })

        if not validated_files:
            raise ValueError("Debug agent returned no valid files")

        # =========================
        # DEBUG SUMMARY
        # =========================
        debug_summary = parsed.get("debug_summary", {
            "root_cause": "Not provided",
            "fix": "Not provided"
        })

        # =========================
        # Langfuse span end
        # =========================
        if span:
            span.end(
                output={
                    "files_updated": len(validated_files),
                    "root_cause": debug_summary.get("root_cause"),
                    "fix": debug_summary.get("fix")
                }
            )

        return {
            "files": validated_files,
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
