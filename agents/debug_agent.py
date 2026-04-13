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


# 🔥 NEW: SYNTAX FIX DETECTOR
def _is_syntax_error(error_log):
    if not isinstance(error_log, str):
        return False

    error_log = error_log.lower()

    return any(x in error_log for x in [
        "syntax error",
        "missing ';'",
        "expected ';'",
        "error c2059",
        "error c2143"
    ])


# 🔥 NEW: HARD FIX FOR TEST FILE
def _force_syntax_fix(files):
    fixed_files = []

    for f in files:
        content = f["content"]

        # simple brace balance fix
        open_braces = content.count("{")
        close_braces = content.count("}")

        if open_braces > close_braces:
            content += "\n}" * (open_braces - close_braces)

        # ensure file ends cleanly
        content = content.rstrip() + "\n"

        fixed_files.append({
            "filename": f["filename"],
            "content": content
        })

    print("SENDING: {'step': 'syntax_fix_applied'}")

    return fixed_files


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

    # 🔥 STEP 1: HANDLE SYNTAX ERRORS FIRST (DETERMINISTIC)
    if _is_syntax_error(error_log):
        print("SENDING: {'step': 'syntax_error_detected'}")

        fixed = _force_syntax_fix(files)

        return {
            "files": fixed,
            "debug_summary": {
                "root_cause": "Syntax error in generated code",
                "fix": "Applied automatic brace/structure correction"
            }
        }

    # 🔥 STEP 2: LLM FIX
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
- DO NOT return identical code

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

        # ensure all files present
        returned = {f["filename"] for f in updated_files}
        for f in files:
            if f["filename"] not in returned:
                updated_files.append(f)

        # 🔥 STEP 3: FORCE CHANGE IF LLM FAILS
        if not _files_changed(files, updated_files):
            print("SENDING: {'step': 'debug_no_change_detected'}")

            # 🔥 FORCE MINIMAL CHANGE (avoid stagnation)
            forced = []
            for f in files:
                forced.append({
                    "filename": f["filename"],
                    "content": f["content"] + "\n// debug iteration fix\n"
                })

            print("SENDING: {'step': 'forced_change_applied'}")

            return {
                "files": forced,
                "debug_summary": {
                    "root_cause": "LLM failed to modify code",
                    "fix": "Forced minimal change to trigger rewrite"
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
