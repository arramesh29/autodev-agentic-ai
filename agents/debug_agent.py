from services.llm_service import llm
import json
import re


def _normalize_files(files):
    """Ensure safe structure for files"""
    normalized = []

    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        return []

    for f in files:
        if isinstance(f, dict):
            filename = f.get("filename")
            content = f.get("content")

            if isinstance(filename, str) and isinstance(content, str):
                normalized.append({
                    "filename": filename.strip(),
                    "content": content
                })

    return normalized


def fix_code(error_log, files, trace=None, parent_span=None):

    # 🔥 Normalize incoming files (CRITICAL)
    files = _normalize_files(files)

    span = None
    if trace:
        span = (
            parent_span.span(name="fix_code_agent")
            if parent_span
            else trace.span(name="fix_code_agent")
        )

    original_filenames = {f["filename"] for f in files}

    # =========================
    # 🔥 STRICT PROMPT
    # =========================
    prompt = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

FILES:
{files}

=========================
CRITICAL INSTRUCTIONS
=========================

- Fix the issue in the code
- Modify logic if required
- Handle edge cases (NaN, infinity)
- If the failure is with test case, modify test case
- Return ALL the 3 files specified in format always

=========================
STRICT OUTPUT FORMAT
=========================

Return ONLY valid JSON.

Schema:

{{
  "files": [
    {{
      "filename": "string",
      "content": "string"
    }}
  ],
  "debug_summary": {{
    "root_cause": "string",
    "fix": "string"
  }}
}}

=========================
STRICT RULES
=========================

- "files" MUST be a list
- Each item MUST be an object
- NO strings inside "files"

❌ INVALID:
"files": ["code"]

❌ INVALID:
"files": "string"

❌ INVALID:
missing filename/content

✅ VALID:
Files Format:

{{
  "files":[
    {{"filename":"aeb_controller.h","content":"header code"}},
    {{"filename":"aeb_controller.cpp","content":"implementation"}},
    {{"filename":"test_aeb_controller.cpp","content":"GoogleTest code"}}
  ]
}}

If format is wrong, system will reject your response.

Return ONLY JSON.
"""

    text = None

    try:
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

        # =========================
        # 🔥 CLEAN RESPONSE
        # =========================
        text = text.replace("```json", "").replace("```", "").strip()

        if text.lower().startswith("json"):
            text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON found")

        json_str = text[start:end + 1]

        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        parsed = json.loads(json_str)

        updated_files = parsed.get("files", [])

        # =========================
        # 🔥 SANITIZE OUTPUT (CRITICAL FIX)
        # =========================
        updated_files = _normalize_files(updated_files)

        # =========================
        # 🔥 FALLBACK IF EMPTY
        # =========================
        if not updated_files:
            print("⚠️ No valid files from LLM → fallback to previous files")
            updated_files = files

        # =========================
        # 🔥 ENSURE COMPLETENESS
        # =========================
        returned = {f["filename"] for f in updated_files}

        for f in files:
            if f["filename"] not in returned:
                updated_files.append(f)

        debug_summary = parsed.get("debug_summary", {
            "root_cause": "Not provided",
            "fix": "Not provided"
        })

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

        print(f"⚠️ Debug agent error: {e}")

        if span:
            span.end(level="ERROR", status_message=str(e))

        # 🔥 NEVER BREAK WORKFLOW
        return {
            "files": files,
            "debug_summary": {
                "root_cause": "Debug failed",
                "fix": "No changes applied"
            }
        }
