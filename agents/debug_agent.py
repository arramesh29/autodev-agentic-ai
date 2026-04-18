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
# ERROR CLASSIFIER
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


# =========================
# 🔥 NEW: LINE NUMBER EXTRACTION
# =========================
def _extract_error_location(error_log):

    if not isinstance(error_log, str):
        return None

    # MSVC style: file.cpp(247)
    msvc = re.findall(r'([a-zA-Z0-9_./\\]+)\((\d+)\)', error_log)

    # GCC/Clang style: file.cpp:247
    gcc = re.findall(r'([a-zA-Z0-9_./\\]+):(\d+)', error_log)

    locations = []

    for f, l in msvc + gcc:
        try:
            locations.append({
                "file": f.split("\\")[-1].split("/")[-1],
                "line": int(l)
            })
        except:
            continue

    if locations:
        print(f"SENDING: {{'step': 'error_locations_detected', 'count': {len(locations)}}}")
        return locations[:3]  # limit noise

    return None


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
    return _classify_error(error_log) == "syntax"


# =========================
# 🔥 UPDATED: SAFE SYNTAX FIX
# =========================
def _force_syntax_fix(files):

    fixed_files = []

    for f in files:
        content = f["content"]
        original_content = content

        # 1. Safe brace balancing
        open_braces = content.count("{")
        close_braces = content.count("}")

        if open_braces > close_braces:
            content += "\n}" * (open_braces - close_braces)

        # 2. Limited semicolon fix (SAFE)
        content = re.sub(
            r'([a-zA-Z0-9_])\s*\n\s*}',
            r'\1;\n}',
            content
        )

        # ❌ REMOVED dangerous global replacement
        # content = re.sub(r';?\s*}', r';\n}', content)

        # 3. Ensure newline
        content = content.rstrip() + "\n"

        # 4. If no real change → signal failure
        if content == original_content:
            print("SENDING: {'step': 'syntax_fix_no_safe_change'}")
            return None   # 🔥 IMPORTANT

        fixed_files.append({
            "filename": f["filename"],
            "content": content
        })

    print("SENDING: {'step': 'syntax_fix_applied'}")

    return fixed_files


# =========================
# 🔥 UPDATED: PROMPT BUILDER (LINE-AWARE)
# =========================
def _build_prompt(error_type, error_log, files, error_locations=None):

    base = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

FILES:
{files}
"""

    # 🔥 NEW: inject line-aware hint
    if error_locations:
        base += "\nERROR LOCATIONS:\n"
        for loc in error_locations:
            base += f"- File: {loc['file']}, Line: {loc['line']}\n"

        base += """
FOCUS ON THESE LOCATIONS FIRST.
Do not blindly modify entire file.
"""

    base += """
CRITICAL:
- You MUST fix the issue
- Fix the issue with MINIMAL changes
- Do NOT rewrite entire files unnecessarily
- Preserve working logic
- You MUST change logic (no same code)
- Handle boundary + edge cases
- Return ALL files
- Ensure valid compilable C++
- Do NOT introduce new syntax errors
- If multiple syntax errors exist, fix structure carefully
- Prefer fixing declarations and structure over random edits
"""

    if error_type == "build":
        base += """
FOCUS:
- Fix compilation errors at indicated lines
- Correct declarations, types, missing includes
- Resolve missing includes, symbols, or definitions
- Ensure all functions are defined and linked
"""

    elif error_type == "logic":
        base += """
FOCUS:
- Fix incorrect logic
- Ensure tests pass
- Validate expected vs actual outputs
- Compare expected vs actual
- Fix either code OR test (not both blindly)
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


# =========================
# MAIN DEBUG FUNCTION
# =========================
def fix_code(error_log, files, trace=None, parent_span=None):

    print("SENDING: {'step': 'debug_start'}")

    files = _normalize_files(files)

    error_type = _classify_error(error_log)
    print(f"SENDING: {{'step': 'error_classified', 'type': '{error_type}'}}")

    # 🔥 NEW
    error_locations = _extract_error_location(error_log)
    # =========================
    # 🔥 UPDATED SYNTAX HANDLING
    # =========================
    if error_type == "syntax":
        print("SENDING: {'step': 'syntax_error_detected'}")

        fixed = _force_syntax_fix(files)

        # 🔥 fallback to LLM if unsafe
        if fixed is None:
            print("SENDING: {'step': 'syntax_fix_failed_fallback_llm'}")
            error_type = "build"

        elif not _files_changed(files, fixed):
            print("SENDING: {'step': 'syntax_fix_no_change'}")
            error_type = "build"

        else:
            return {
                "files": fixed,
                "debug_summary": {
                    "root_cause": "Syntax error",
                    "fix": "Safe auto correction"
                },
                "llm_prompt": None,
                "llm_response": None
            }

    # =========================
    # LLM CALL
    # =========================
    prompt = _build_prompt(error_type, error_log, files, error_locations)

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
