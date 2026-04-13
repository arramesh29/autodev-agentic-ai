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


def fix_code(error_log, files, trace=None, parent_span=None):

    files = _normalize_files(files)

    span = None
    if trace:
        span = (
            parent_span.span(name="fix_code_agent")
            if parent_span
            else trace.span(name="fix_code_agent")
        )

    original_files = files

    # 🔁 MULTI-ATTEMPT DEBUG (CRITICAL FIX)
    MAX_INTERNAL_RETRY = 2

    for attempt in range(MAX_INTERNAL_RETRY):

        print(f"SENDING: {{'step': 'debug_attempt', 'attempt': {attempt}}}")

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
- You MUST change logic if previous attempt failed
- If same failure repeats, rethink approach
- Handle edge cases (NaN, infinity)
- If test is wrong, fix test
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
                continue

            # CLEAN
            text = text.replace("```json", "").replace("```", "").strip()

            if text.lower().startswith("json"):
                text = text[4:].strip()

            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1:
                continue

            json_str = text[start:end + 1]

            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)

            parsed = json.loads(json_str)

            updated_files = _normalize_files(parsed.get("files", []))

            if not updated_files:
                continue

            # 🔥 ENSURE COMPLETENESS
            returned = {f["filename"] for f in updated_files}
            for f in original_files:
                if f["filename"] not in returned:
                    updated_files.append(f)

            # 🔥 KEY FIX: detect no change
            if not _files_changed(original_files, updated_files):
                print("SENDING: {'step': 'debug_no_change'}")
                continue

            print("SENDING: {'step': 'debug_fix_applied'}")

            debug_summary = parsed.get("debug_summary", {})

            return {
                "files": updated_files,
                "debug_summary": debug_summary
            }

        except Exception as e:
            print(f"SENDING: {{'step': 'debug_error', 'message': '{str(e)}'}}")
            continue

    # 🔥 FINAL FALLBACK
    print("SENDING: {'step': 'debug_fallback'}")

    return {
        "files": original_files,
        "debug_summary": {
            "root_cause": "No effective fix generated",
            "fix": "Retry attempts exhausted"
        }
    }
