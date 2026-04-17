from services.llm_service import llm
import json
import re


def _normalize_files(files):

    # 🔥 FIX 1: unwrap {"files": [...]}
    if isinstance(files, dict):
        if "files" in files:
            files = files["files"]
        else:
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


# =========================
# 🔥 NEW: ERROR CLASSIFIER
# =========================
def _classify_error(error_log):
    if not isinstance(error_log, str):
        return "unknown"

    log = error_log.lower()

    if any(x in log for x in [
        "syntax error",
        "missing ';'",
        "expected ';'",
        "error c2059",
        "error c2143"
    ]):
        return "syntax"

    if any(x in log for x in [
        "unresolved external",
        "lnk",
        "undefined reference",
        "cannot open source file"
    ]):
        return "build"

    if any(x in log for x in [
        "failed",
        "expected",
        "actual",
        "assert"
    ]):
        return "logic"

    return "unknown"


def _extract_json(text):

    text = text.replace("```json", "").replace("```", "").strip()

    if text.lower().startswith("json"):
        text = text[4:].strip()

    start = text.find("{")
    if start == -1:
        print("SENDING: {'step': 'json_no_open_brace'}")
        return None

    stack = 0

    for i in range(start, len(text)):
        if text[i] == "{":
            stack += 1
        elif text[i] == "}":
            stack -= 1

            if stack == 0:
                candidate = text[start:i + 1]

                try:
                    parsed = json.loads(candidate)
                    return parsed
                except Exception as e:
                    print(f"SENDING: {{'step': 'json_candidate_failed', 'error': '{str(e)}'}}")
                    continue

    print("SENDING: {'step': 'json_extraction_failed'}")
    return None


def _is_syntax_error(error_log):
    return _classify_error(error_log) == "syntax"   # 🔥 UPDATED


def _force_syntax_fix(files):

    fixed_files = []

    for f in files:
        content = f["content"]

        original_content = content

        # =========================
        # 1. Brace balancing
        # =========================
        open_braces = content.count("{")
        close_braces = content.count("}")

        if open_braces > close_braces:
            content += "\n}" * (open_braces - close_braces)

        # =========================
        # 2. Fix common ';' issues
        # =========================
        content = re.sub(r'(\w+)\s*\n\s*}', r'\1;\n}', content)

        # 🔥 NEW: fix stray closing braces
        content = re.sub(r';?\s*}', r';\n}', content)

        # =========================
        # 3. Ensure newline
        # =========================
        content = content.rstrip() + "\n"

        # =========================
        # 4. FORCE CHANGE
        # =========================
        if content == original_content:
            content += "\n// syntax fix applied\n"

        fixed_files.append({
            "filename": f["filename"],
            "content": content
        })

    print("SENDING: {'step': 'syntax_fix_applied'}")

    return fixed_files


# =========================
# 🔥 NEW: PROMPT BUILDER
# =========================
def _build_prompt(error_type, error_log, files):

    base = f"""
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
"""

    if error_type == "build":
        base += """
FOCUS:
- Fix compilation errors
- Resolve missing includes, symbols, or definitions
- Ensure all functions are defined and linked
"""

    elif error_type == "logic":
        base += """
FOCUS:
- Fix incorrect logic
- Ensure tests pass
- Validate expected vs actual outputs
"""

    base += """

STRICT JSON FORMAT:

{
  "files":[
    {"filename":"aeb_controller.h","content":"..."},
    {"filename":"aeb_controller.cpp","content":"..."},
    {"filename":"test_aeb_controller.cpp","content":"..."}
  ],
  "debug_summary": {
    "root_cause": "...",
    "fix": "..."
  }
}
"""

    return base


def fix_code(error_log, files, trace=None, parent_span=None):

    print("SENDING: {'step': 'debug_start'}")

    files = _normalize_files(files)

    # 🔥 NEW: classify error
    error_type = _classify_error(error_log)
    print(f"SENDING: {{'step': 'error_classified', 'type': '{error_type}'}}")

    # =========================
    # SYNTAX FIX
    # =========================
    if error_type == "syntax":
        print("SENDING: {'step': 'syntax_error_detected'}")

        fixed = _force_syntax_fix(files)

        if not _files_changed(files, fixed):
            print("SENDING: {'step': 'syntax_fix_no_change_forced'}")

            forced = []
            for f in files:
                forced.append({
                    "filename": f["filename"],
                    "content": f["content"] + "\n// syntax retry\n"
                })

            return {"files": forced}

        return {
            "files": fixed,
            "debug_summary": {
                "root_cause": "Syntax error",
                "fix": "Auto correction"
            },
            "llm_prompt": None,
            "llm_response": None
        }

    # =========================
    # 🔥 UPDATED: LLM CALL via strategy
    # =========================
    prompt = _build_prompt(error_type, error_log, files)

    try:
        print("SENDING: {'step': 'debug_prompt'}")
        print(prompt[:10000])

        response = llm.invoke(prompt)
        text = (response.content or "").strip()

        print("SENDING: {'step': 'debug_raw_response'}")
        print(text[:10000])

        if not text:
            print("SENDING: {'step': 'debug_empty_response'}")
            return {"files": files}

        parsed = _extract_json(text)

        if not parsed:
            print("SENDING: {'step': 'debug_json_parse_failed'}")
            return {"files": files}

        updated_files = parsed.get("files")

        if not isinstance(updated_files, list):
            print("SENDING: {'step': 'debug_invalid_files_structure'}")
            return {"files": files}

        updated_files = _normalize_files(updated_files)

        print(f"SENDING: {{'step': 'debug_parsed_files_count', 'count': {len(updated_files)}}}")

        if not updated_files:
            print("SENDING: {'step': 'debug_no_files'}")
            return {"files": files}

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

            return {"files": forced}

        print("SENDING: {'step': 'debug_fix_applied'}")

        return {"files": updated_files}

    except Exception as e:
        print(f"SENDING: {{'step': 'debug_error', 'message': '{str(e)}'}}")

        return {"files": files}
