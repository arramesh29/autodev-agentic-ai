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
        # 🔥 SAFE LLM CALL
        # =========================
        response = llm.invoke(prompt)
        text = (response.content or "").strip()

        if not text:
            raise ValueError("Empty LLM response")

        if generation:
            generation.end(output=text[:2000])

        # =========================
        # 🔥 ROBUST JSON EXTRACTION
        # =========================

        # Remove markdown wrappers safely
        if "```" in text:
            parts = text.split("```")
            for p in parts:
                if "{" in p and "}" in p:
                    text = p
                    break

        # Extract JSON block (non-greedy)
        match = re.search(r"\{[\s\S]*?\}", text)
        if not match:
            raise ValueError("No JSON found in response")

        json_str = match.group(0)

        # Cleanup trailing commas
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
            if isinstance(f, dict):
                filename = f.get("filename")
                content = f.get("content")

                if isinstance(filename, str) and filename.strip() and isinstance(content, str):
                    validated_files.append({
                        "filename": filename.strip(),
                        "content": content
                    })

        if not validated_files:
            raise ValueError("No valid files returned")

        # =========================
        # 🔥 ENSURE COMPLETENESS
        # =========================
        returned_filenames = {f["filename"] for f in validated_files}
        missing = original_filenames - returned_filenames

        if missing:
            for f in files:
                if f["filename"] in missing:
                    validated_files.append(f)

        # =========================
        # 🔥 RELAXED CHANGE CHECK
        # =========================
        old_map = {f["filename"]: f["content"] for f in files}
        new_map = {f["filename"]: f["content"] for f in validated_files}

        changes = sum(
            1 for k in old_map if k not in new_map or old_map[k] != new_map[k]
        )

        if changes == 0:
            print("⚠️ Warning: Debug agent made no visible changes")

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

        raise ValueError(f"Debug agent failed:\n{text if text else 'No response'}")
