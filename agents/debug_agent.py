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

    # Extract original filenames
    original_filenames = set()
    for f in files:
        if isinstance(f, dict) and "filename" in f:
            original_filenames.add(f["filename"])

    prompt = f"""
You are a senior automotive C++ software engineer.

The system failed.

ERROR:
{error_log}

FILES:
{files}

CRITICAL:
- You MUST FIX the issue
- You MUST modify the code
- Do NOT return the same code again
- Handle edge cases like infinity / NaN properly
- Ensure all files are returned

Return ONLY JSON:
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
        if span:
            generation = span.generation(
                name="llm_fix_code",
                model="gpt-4o",
                input=prompt,
                metadata={"agent": "debug_agent"}
            )

        # =========================
        # 🔥 LLM CALL WITH RETRY
        # =========================
        MAX_LLM_RETRY = 2

        for attempt in range(MAX_LLM_RETRY):
            response = llm.invoke(prompt)

            if not response or not hasattr(response, "content"):
                continue

            text = response.content.strip()

            # 🔥 Reject weak responses
            if not text or len(text) < 50:
                continue

            break

        if not text:
            raise ValueError("LLM returned empty/invalid response")

        if generation:
            generation.end(output=text[:2000])

        # =========================
        # JSON EXTRACTION
        # =========================
        cleaned = text.replace("```json", "").replace("```", "")

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in debug agent output")

        json_str = match.group(0)

        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        parsed = json.loads(json_str)

        # =========================
        # VALIDATION
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
        # 🔥 ENSURE ACTUAL CHANGE
        # =========================
        old_map = {f["filename"]: f["content"] for f in files}
        new_map = {f["filename"]: f["content"] for f in validated_files}

        no_change = True
        for k in old_map:
            if k not in new_map or old_map[k] != new_map[k]:
                no_change = False
                break

        if no_change:
            raise ValueError("LLM returned identical code (no fix applied)")

        # =========================
        # COMPLETENESS
        # =========================
        returned_filenames = set(f["filename"] for f in validated_files)
        missing_files = original_filenames - returned_filenames

        if missing_files:
            for f in files:
                if f["filename"] in missing_files:
                    validated_files.append(f)

        debug_summary = parsed.get("debug_summary", {
            "root_cause": "Not provided",
            "fix": "Not provided"
        })

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
            f"Debug agent failed:\n{text if text else 'No response'}"
        )
