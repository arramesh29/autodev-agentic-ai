from services.llm_service import llm
import json
import re


def _normalize_files(files):

    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        print("SENDING: {'step': 'normalize_invalid_input'}")
        return []

    normalized = []

    for idx, f in enumerate(files):

        if not isinstance(f, dict):
            print(f"SENDING: {{'step': 'normalize_invalid_item', 'index': {idx}}}")
            continue

        filename = f.get("filename")
        content = f.get("content")

        if not isinstance(filename, str) or not filename.strip():
            print(f"SENDING: {{'step': 'normalize_invalid_filename', 'index': {idx}}}")
            continue

        if not isinstance(content, str):
            print(f"SENDING: {{'step': 'normalize_invalid_content', 'file': '{filename}'}}")
            continue

        normalized.append({
            "filename": filename.strip(),
            "content": content
        })

    print(f"SENDING: {{'step': 'normalize_success', 'count': {len(normalized)}}}")

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

    # 🔥 safer extraction
    matches = re.findall(r"\{[\s\S]*?\}", text)

    for candidate in matches:
        try:
            parsed = json.loads(candidate)
            return parsed
        except Exception:
            continue

    print("SENDING: {'step': 'json_extraction_failed'}")
    return None


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


def _force_syntax_fix(files):

    fixed_files = []

    for f in files:
        content = f["content"]

        open_braces = content.count("{")
        close_braces = content.count("}")

        if open_braces > close_braces:
            content += "\n}" * (open_braces - close_braces)

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

    # =========================
    # SYNTAX FIX
    # =========================
    if _is_syntax_error(error_log):
        print("SENDING: {'step': 'syntax_error_detected'}")

        fixed = _force_syntax_fix(files)

        return {
            "files": fixed,
            "debug_summary": {
                "root_cause": "Syntax error",
                "fix": "Auto brace correction"
            },
            "llm_prompt": None,
            "llm_response": None
        }

    # =========================
    # LLM CALL
    # =========================
    prompt = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

FILES:
{files}

CRITICAL:
- You MUST fix the issue
- You MUST change logic (no same code)
- Handle boundary + edge cases
- Return ALL files
- Ensure valid compilable C++

STRICT JSON FORMAT:

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
        print("SENDING: {'step': 'debug_prompt'}")
        print(prompt[:1000])

        response = llm.invoke(prompt)
        text = (response.content or "").strip()

        print("SENDING: {'step': 'debug_raw_response'}")
        print(text[:1000])

        if not text:
            print("SENDING: {'step': 'debug_empty_response'}")
            return {"files": files, "llm_prompt": prompt, "llm_response": text}

        parsed = _extract_json(text)

        if not parsed:
            print("SENDING: {'step': 'debug_json_parse_failed'}")
            return {"files": files, "llm_prompt": prompt, "llm_response": text}

        updated_files = parsed.get("files")

        if not isinstance(updated_files, list):
            print("SENDING: {'step': 'debug_invalid_files_structure'}")
            return {"files": files, "llm_prompt": prompt, "llm_response": text}

        updated_files = _normalize_files(updated_files)

        print(f"SENDING: {{'step': 'debug_parsed_files_count', 'count': {len(updated_files)}}}")

        if not updated_files:
            print("SENDING: {'step': 'debug_no_files'}")
            return {"files": files, "llm_prompt": prompt, "llm_response": text}

        # ensure all files present
        returned = {f["filename"] for f in updated_files}
        for f in files:
            if f["filename"] not in returned:
                updated_files.append(f)

        # =========================
        # FORCE CHANGE
        # =========================
        if not _files_changed(files, updated_files):
            print("SENDING: {'step': 'debug_no_change_detected'}")

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
                    "root_cause": "LLM returned unchanged code",
                    "fix": "Forced mutation"
                },
                "llm_prompt": prompt,
                "llm_response": text
            }

        print("SENDING: {'step': 'debug_fix_applied'}")

        return {
            "files": updated_files,
            "debug_summary": parsed.get("debug_summary", {}),
            "llm_prompt": prompt,
            "llm_response": text
        }

    except Exception as e:
        print(f"SENDING: {{'step': 'debug_error', 'message': '{str(e)}'}}")

        return {
            "files": files,
            "debug_summary": {
                "root_cause": "Exception",
                "fix": str(e)
            },
            "llm_prompt": prompt,
            "llm_response": str(e)
        }
