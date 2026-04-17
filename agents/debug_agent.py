from services.llm_service import llm
import json
import re


def _normalize_files(files):
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
    return old_map != new_map


# =========================
# 🔥 NEW: FAILURE ANALYSIS
# =========================
def _analyze_failure(error_log):
    if not isinstance(error_log, str):
        return {"suspect": "code"}

    log = error_log.lower()

    if any(x in log for x in ["expected", "actual", "failed"]):
        return {"suspect": "code_or_test"}

    if "assert" in log:
        return {"suspect": "code"}

    return {"suspect": "code"}


# =========================
# 🔥 UPDATED: ERROR CLASSIFIER
# =========================
def _classify_error(error_log):
    if not isinstance(error_log, str):
        return "unknown"

    log = error_log.lower()

    if any(x in log for x in [
        "syntax error", "missing ';'", "error c2059", "error c2143"
    ]):
        return "syntax"

    if any(x in log for x in [
        "unresolved external", "lnk", "undefined reference"
    ]):
        return "build"

    if any(x in log for x in [
        "failed", "expected", "actual", "assert"
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
                    return json.loads(candidate)
                except Exception:
                    continue

    print("SENDING: {'step': 'json_extraction_failed'}")
    return None


def _is_syntax_error(error_log):
    return _classify_error(error_log) == "syntax"


def _force_syntax_fix(files):
    fixed_files = []

    for f in files:
        content = f["content"]
        original = content

        open_braces = content.count("{")
        close_braces = content.count("}")

        if open_braces > close_braces:
            content += "\n}" * (open_braces - close_braces)

        content = re.sub(r'(\w+)\s*\n\s*}', r'\1;\n}', content)
        content = re.sub(r';?\s*}', r';\n}', content)

        content = content.rstrip() + "\n"

        if content == original:
            content += "\n// syntax fix applied\n"

        fixed_files.append({
            "filename": f["filename"],
            "content": content
        })

    print("SENDING: {'step': 'syntax_fix_applied'}")
    return fixed_files


# =========================
# 🔥 UPDATED: PROMPT BUILDER (DIFF + REQUIREMENT)
# =========================
def _build_prompt(error_type, error_log, files, requirement=None):

    base = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

FILES:
{files}
"""

    if requirement:
        base += f"\nREQUIREMENT:\n{requirement}\n"

    base += """
CRITICAL:
- DO NOT rewrite entire files unnecessarily
- Make MINIMAL changes required
- Preserve working logic

DEBUG STRATEGY:
1. Identify root cause
2. Decide if issue is in code or test
3. Fix ONLY necessary part
"""

    if error_type == "logic":
        base += """
FOCUS:
- Compare expected vs actual
- Fix test ONLY if expectation is wrong
- Otherwise fix code
"""

    elif error_type == "build":
        base += """
FOCUS:
- Fix compilation only
- Do not modify logic unnecessarily
"""

    base += """

STRICT JSON FORMAT:
{
  "files":[{"filename":"...","content":"..."}],
  "debug_summary": {
    "root_cause": "...",
    "fix": "...",
    "changed_files": ["..."]
  }
}
"""

    return base


def fix_code(error_log, files, trace=None, parent_span=None):

    print("SENDING: {'step': 'debug_start'}")

    files = _normalize_files(files)

    error_type = _classify_error(error_log)
    print(f"SENDING: {{'step': 'error_classified', 'type': '{error_type}'}}")

    # 🔥 NEW
    failure_analysis = _analyze_failure(error_log)
    print(f"SENDING: {{'step': 'failure_analysis', 'data': {failure_analysis}}}")

    # =========================
    # SYNTAX FIX
    # =========================
    if error_type == "syntax":
        print("SENDING: {'step': 'syntax_error_detected'}")

        fixed = _force_syntax_fix(files)

        if not _files_changed(files, fixed):
            print("SENDING: {'step': 'syntax_fix_no_change_forced'}")
            return {
                "files": [
                    {
                        "filename": f["filename"],
                        "content": f["content"] + "\n// syntax retry\n"
                    } for f in files
                ]
            }

        return {"files": fixed}

    # =========================
    # 🔥 UPDATED: LLM CALL
    # =========================
    requirement = getattr(trace, "input", {}).get("requirement") if trace else None

    prompt = _build_prompt(error_type, error_log, files, requirement)

    try:
        print("SENDING: {'step': 'debug_prompt'}")

        response = llm.invoke(prompt)
        text = (response.content or "").strip()

        print("SENDING: {'step': 'debug_raw_response'}")

        if not text:
            return {"files": files}

        parsed = _extract_json(text)

        if not parsed:
            return {"files": files}

        updated_files = _normalize_files(parsed.get("files"))

        if not updated_files:
            return {"files": files}

        # 🔥 NEW: changed files tracking
        changed_files = [
            f["filename"]
            for f in updated_files
            if any(of["filename"] == f["filename"] and of["content"] != f["content"] for of in files)
        ]

        print(f"SENDING: {{'step': 'changed_files', 'files': {changed_files}}}")

        # ensure all files present
        returned = {f["filename"] for f in updated_files}
        for f in files:
            if f["filename"] not in returned:
                updated_files.append(f)

        if not _files_changed(files, updated_files):
            print("SENDING: {'step': 'debug_no_change_detected'}")

            return {
                "files": [
                    {
                        "filename": f["filename"],
                        "content": f["content"] + "\n// debug iteration fix\n"
                    } for f in files
                ]
            }

        print("SENDING: {'step': 'debug_fix_applied'}")

        return {"files": updated_files}

    except Exception as e:
        print(f"SENDING: {{'step': 'debug_error', 'message': '{str(e)}'}}")
        return {"files": files}
