from services.llm_service import llm
from tools.rag.rag_orchestrator import retrieve_context
import json
import re


# =========================
# 🔥 NEW: EXTRACT REQ IDs (UNCHANGED)
# =========================
def _extract_req_ids(text):
    if not isinstance(text, str):
        return []
    return list(set(re.findall(r"REQ-\d+", text)))


# =========================
# 🔥 NEW: MAP ERROR → REQ (UNCHANGED)
# =========================
def _map_error_to_requirements(error_log, files):
    req_ids = set()

    for f in files:
        req_ids.update(_extract_req_ids(f.get("content", "")))

    req_ids.update(_extract_req_ids(error_log))

    if req_ids:
        print(f"SENDING: {{'step': 'req_mapping_detected', 'req_ids': {list(req_ids)}}}")

    return list(req_ids)


# =========================
# 🔥 NEW: GET EXISTING FILENAMES (ADDED)
# =========================
def _get_existing_filenames(files):
    return [
        f.get("filename")
        for f in files
        if isinstance(f, dict) and f.get("filename")
    ]


# =========================
# EXISTING (UNCHANGED)
# =========================
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

    for k in old_map:
        if k not in new_map or old_map[k] != new_map[k]:
            return True
    return False


def _classify_error(error_log):
    if not isinstance(error_log, str):
        return "unknown"

    log = error_log.lower()

    if any(x in log for x in [
        "syntax error", "missing ';'", "expected ';'", "error c2059", "error c2143"
    ]):
        return "syntax"

    if any(x in log for x in [
        "unresolved external", "lnk", "undefined reference", "cannot open source file"
    ]):
        return "build"

    if any(x in log for x in [
        "failed", "expected", "actual", "assert"
    ]):
        return "logic"

    return "unknown"


def _extract_error_location(error_log):
    if not isinstance(error_log, str):
        return None

    msvc = re.findall(r'([a-zA-Z0-9_./\\]+)\((\d+)\)', error_log)
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
        return locations[:3]

    return None

def _extract_file_context(
    files,
    error_locations,
    radius=20
):

    if not error_locations:
        return files

    reduced = []

    for f in files:

        filename = f["filename"]

        matching = [
            loc
            for loc in error_locations
            if loc["file"] == filename
        ]

        if not matching:
            continue

        lines = f["content"].splitlines()

        snippets = []

        for loc in matching:

            line_no = loc["line"]

            start = max(
                0,
                line_no - radius
            )

            end = min(
                len(lines),
                line_no + radius
            )

            snippet = "\n".join(
                lines[start:end]
            )

            snippets.append(
                f"\n=== ERROR AREA "
                f"(line {line_no}) ===\n"
                f"{snippet}"
            )

        reduced.append({

            "filename":
                filename,

            "content":
                "\n".join(snippets)
        })

    return reduced or files

def _extract_json(text):

    if not text:
        return None

    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    candidates = []

    start_positions = [
        i for i, ch in enumerate(text)
        if ch == "{"
    ]

    for start in start_positions:

        stack = 0

        for i in range(start, len(text)):

            if text[i] == "{":
                stack += 1

            elif text[i] == "}":
                stack -= 1

                if stack == 0:

                    candidate = text[start:i + 1]
                    candidates.append(candidate)
                    break

    candidates.sort(
        key=len,
        reverse=True
    )

    for candidate in candidates:

        try:

            return json.loads(candidate)

        except Exception as e:

            print(
                f"SENDING: "
                f"{{'step':'json_candidate_failed',"
                f"'error':'{str(e)}'}}"
            )

    print(
        "SENDING: "
        "{'step':'json_extraction_failed'}"
    )

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

        open_braces = content.count("{")
        close_braces = content.count("}")

        if open_braces > close_braces:
            content += "\n}" * (open_braces - close_braces)

        content = re.sub(
            r'([a-zA-Z0-9_])\s*\n\s*}',
            r'\1;\n}',
            content
        )

        content = content.rstrip() + "\n"

        if content == original_content:
            print("SENDING: {'step': 'syntax_fix_no_safe_change'}")
            return None

        fixed_files.append({
            "filename": f["filename"],
            "content": content
        })

    print("SENDING: {'step': 'syntax_fix_applied'}")

    return fixed_files


# =========================
# 🔥 FIXED PROMPT (ONLY CHANGE)
# =========================
def _build_prompt(error_type, error_log, files, error_locations=None, req_ids=None):

    filenames = _get_existing_filenames(files)

    rag_context = retrieve_context(
        error_log,
        "debug")
    
    base = f"""
You are a senior automotive C++ engineer.

ERROR:
{error_log}

REFERENCE CONTEXT:
{rag_context}

FILES:
{json.dumps(files, indent=2)}
"""

    if req_ids:
        base += f"\nAFFECTED REQUIREMENTS: {req_ids}\n"
        base += """
Focus on logic related to these REQ-IDs.
Ensure requirement correctness is preserved.
Do not blindly modify entire file.
"""

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
- Fix the issue with minimal changes
- Preserve logic and REQ traceability
- DO NOT rename files
- Use EXACT filenames below
- Handle boundary + edge cases
- Return ALL files
- Valid compilable C++
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
    base += f"""
FILENAMES:
{filenames}

STRICT JSON FORMAT:

{{
  "files":[
    {", ".join([f'{{"filename":"{fn}","content":"..."}}' for fn in filenames])}
  ],
  "debug_summary": {{
    "root_cause": "...",
    "fix": "..."
  }}
}}
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

    error_locations = _extract_error_location(error_log)
    req_ids = _map_error_to_requirements(error_log, files)

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

    prompt_files = _extract_file_context(
        files,
        error_locations
    )

    prompt = _build_prompt(
        error_type,
        error_log,
        prompt_files,
        error_locations,
        req_ids
    )

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
        
            print(
                "SENDING: "
                "{'step':'debug_json_repair_attempt'}"
            )
        
            try:
        
                repair_prompt = f"""
        Return ONLY valid JSON.
        
        Do not include markdown.
        Do not include explanations.
        
        Previous response:
        
        {text}
        """
        
                repair_response = llm.invoke(
                    repair_prompt
                )
        
                repair_text = (
                    repair_response.content or ""
                ).strip()
        
                parsed = _extract_json(
                    repair_text
                )
        
                if parsed:
        
                    print(
                        "SENDING: "
                        "{'step':'debug_json_repair_success'}"
                    )
        
            except Exception as e:
        
                print(
                    f"SENDING: "
                    f"{{'step':'debug_json_repair_failed',"
                    f"'error':'{str(e)}'}}"
                )
        
        if not parsed:
        
            print(
                "SENDING: "
                "{'step':'debug_json_parse_failed'}"
            )
        
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
