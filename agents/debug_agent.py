from services.llm_service import llm
import json


def normalize_files(files):
    if isinstance(files, dict):
        files = files.get("files", [])

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


def files_changed(old_files, new_files):
    old_map = {f["filename"]: f["content"] for f in old_files}
    new_map = {f["filename"]: f["content"] for f in new_files}
    return old_map != new_map


def fix_code(error_log, files, trace=None, parent_span=None):

    print("SENDING: {'step': 'debug_start'}")

    files = normalize_files(files)

    prompt = f"""
You are a senior automotive C++ engineer.

FAILURE:
{error_log}

FILES:
{files}

CRITICAL:
- Fix ONLY the failing test
- Focus on TTC threshold logic
- Ensure:
    OperatingMode::kFcwActive is triggered when TTC < warning threshold
    warning_level = WarningLevel::kVisual
    critical_ttc_s is correctly computed
- Do NOT rewrite architecture
- Return ALL files

STRICT JSON:
{{
  "files":[
    {{"filename":"aeb_controller.h","content":"..."}},
    {{"filename":"aeb_controller.cpp","content":"..."}},
    {{"filename":"test_aeb_controller.cpp","content":"..."}}
  ]
}}
"""

    try:
        print("SENDING: {'step': 'debug_prompt'}")

        response = llm.invoke(prompt)
        text = (response.content or "").strip()

        print("SENDING: {'step': 'debug_raw_response'}")

        if not text:
            return {"files": files}

        parsed = json.loads(text)

        updated_files = normalize_files(parsed.get("files"))

        if not updated_files:
            print("SENDING: {'step': 'debug_no_files'}")
            return {"files": files}

        if not files_changed(files, updated_files):
            print("SENDING: {'step': 'debug_no_change_detected'}")
            return {"files": files}

        print("SENDING: {'step': 'debug_fix_applied'}")

        return {"files": updated_files}

    except Exception as e:
        print(f"SENDING: {{'step': 'debug_error', 'message': '{str(e)}'}}")
        return {"files": files}
