from services.llm_service import llm
import json
import re


def fix_code(error_log, files, trace=None, parent_span=None):

    span = None
    if trace:
        span = (
            parent_span.span(name="fix_code_agent")
            if parent_span
            else trace.span(name="fix_code_agent")
        )

    original_filenames = {
        f["filename"] for f in files if isinstance(f, dict) and "filename" in f
    }

    prompt = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

FILES:
{files}

CRITICAL:
- You MUST fix the issue
- You MUST change code if needed
- Handle edge cases (NaN, infinity)
- Return ALL files
- Do NOT return unchanged code

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
        MAX_RETRY = 5
        for _ in range(MAX_RETRY):
            response = llm.invoke(prompt)

            if not response or not hasattr(response, "content"):
                continue

            text = (response.content or "").strip()

            if text and len(text) > 30:
                break

        if not text:
            raise ValueError("Empty LLM response")

        if generation:
            generation.end(output=text[:2000])

        # =========================
        # 🔥 ROBUST CLEANING
        # =========================
        text = text.replace("```json", "").replace("```", "").strip()

        # handle "json\n{...}"
        if text.lower().startswith("json"):
            text = text[4:].strip()

        # extract JSON safely using boundaries
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON boundaries found")

        json_str = text[start:end + 1]

        # cleanup trailing commas
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        parsed = json.loads(json_str)

        # =========================
        # VALIDATION (UNCHANGED)
        # =========================
        updated_files = parsed.get("files", [])

        if isinstance(updated_files, dict):
            updated_files = [updated_files]

        if not isinstance(updated_files, list):
            raise ValueError("files must be a list")

        validated_files = []

        for f in updated_files:
            if isinstance(f, dict):
                filename = f.get("filename")
                content = f.get("content")

                if isinstance(filename, str) and filename.strip() and isinstance(content, str):
                    validated_files.append({
                        "filename": filename.strip(),
                        "content": content
                    })

        # =========================
        # 🔥 FALLBACK (NEW)
        # =========================
        if not validated_files:
            print("⚠️ Debug agent returned no valid files → fallback to previous files")
            validated_files = files

        # =========================
        # COMPLETENESS (UNCHANGED)
        # =========================
        returned_filenames = {f["filename"] for f in validated_files}
        missing = original_filenames - returned_filenames

        if missing:
            for f in files:
                if f["filename"] in missing:
                    validated_files.append(f)

        # =========================
        # 🔥 CHANGE DETECTION (IMPROVED)
        # =========================
        old_map = {f["filename"]: f["content"] for f in files}
        new_map = {f["filename"]: f["content"] for f in validated_files}

        changes = sum(
            1 for k in old_map if k not in new_map or old_map[k] != new_map[k]
        )

        if changes == 0:
            print("⚠️ Debug agent made no visible changes")

        debug_summary = parsed.get("debug_summary", {
            "root_cause": "Not provided",
            "fix": "Not provided"
        })

        if span:
            span.end(
                output={
                    "files_updated": len(validated_files),
                    "changes": changes,
                    "root_cause": debug_summary.get("root_cause"),
                    "fix": debug_summary.get("fix")
                }
            )

        return {
            "files": validated_files,
            "debug_summary": debug_summary
        }

    except Exception as e:

        print(f"⚠️ Debug agent error: {e}")

        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": text[:2000] if text else "no response"
                }
            )

        if span:
            span.end(level="ERROR", status_message=str(e))

        # 🔥 CRITICAL: NEVER BREAK WORKFLOW
        return {
            "files": files,
            "debug_summary": {
                "root_cause": "Debug agent failed",
                "fix": "No changes applied"
            }
        }
