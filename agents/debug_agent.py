from services.llm_service import llm
import json
import re


def _normalize_files(files):
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


def _files_changed(old_files, new_files):
    old_map = {f["filename"]: f["content"] for f in old_files}
    new_map = {f["filename"]: f["content"] for f in new_files}

    for k in old_map:
        if k not in new_map or old_map[k] != new_map[k]:
            return True
    return False


def _extract_json(text):
    text = text.replace("```json", "").replace("```", "").strip()

    if text.lower().startswith("json"):
        text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    json_str = text[start:end + 1]

    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    try:
        return json.loads(json_str)
    except Exception:
        return None


def fix_code(error_log, files, trace=None, parent_span=None):

    print("SENDING: {'step': 'debug_start'}")

    files = _normalize_files(files)

    span = None
    if trace:
        span = (
            parent_span.span(name="fix_code_agent")
            if parent_span
            else trace.span(name="fix_code_agent")
        )

    prompt = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

FILES:
{files}

=========================
CRITICAL INSTRUCTIONS
=========================

- You MUST fix the failing test
- You MUST change the logic (do not return same code)
- Carefully handle boundary conditions
- Fix comparison operators if needed (<, <=, >, >=)
- Handle edge cases (zero, negative, infinity)
- If needed, fix test expectations also
- Return ALL files

=========================
STRICT OUTPUT FORMAT
=========================

Return ONLY valid JSON.

{{
  "files":[
    {{"filename":"aeb_controller.h","content":"..."}},
    {{"filename":"aeb_controller.cpp","content":"..."}},
    {{"filename":"test_aeb_controller.cpp","content":"..."}}
  ],
  "debug_summary": {{
    "root_cause": "...",
    "fix": "..."
  }}
}}
"""

    try:
        response = llm.invoke(prompt)
        text = (response.content or "").strip()

        if not text:
            print("SENDING: {'step': 'debug_empty_response'}")
            return {"files": files}

        parsed = _extract_json(text)

        if not parsed:
            print("SENDING: {'step': 'debug_json_parse_failed'}")
            return {"files": files}

        updated_files = _normalize_files(parsed.get("files", []))

        if not updated_files:
            print("SENDING: {'step': 'debug_no_files'}")
            return {"files": files}

        # 🔥 ENSURE ALL FILES PRESENT
        returned = {f["filename"] for f in updated_files}
        for f in files:
            if f["filename"] not in returned:
                updated_files.append(f)

        # 🔥 HARD CHANGE ENFORCEMENT
        if not _files_changed(files, updated_files):
            print("SENDING: {'step': 'debug_no_change_detected'}")

            return {
                "files": files,
                "debug_summary": {
                    "root_cause": "LLM returned unchanged code",
                    "fix": "No changes applied"
                }
            }

        print("SENDING: {'step': 'debug_fix_applied'}")

        return {
            "files": updated_files,
            "debug_summary": parsed.get("debug_summary", {})
        }

    except Exception as e:
        print(f"SENDING: {{'step': 'debug_error', 'message': '{str(e)}'}}")

        return {
            "files": files,
            "debug_summary": {
                "root_cause": "Exception during debug",
                "fix": str(e)
            }
        }
