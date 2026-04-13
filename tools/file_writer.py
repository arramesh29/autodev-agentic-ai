import os


def write_files(files):

    output_dir = "generated"
    os.makedirs(output_dir, exist_ok=True)

    # =========================
    # 🔥 RAW INPUT LOG (NEW)
    # =========================
    print(f"SENDING: {{'step': 'write_input_type', 'type': '{type(files)}'}}")

    if isinstance(files, dict):
        print("SENDING: {'step': 'write_input_dict_wrapped'}")
        files = [files]

    if not isinstance(files, list):
        print("SENDING: {'step': 'write_invalid_input_type'}")
        return {
            "success": False,
            "error": f"Invalid files input type: {type(files)}"
        }

    print(f"SENDING: {{'step': 'write_files_called', 'file_count': {len(files)}}}")

    valid_count = 0
    errors = []
    changed_files = []
    unchanged_files = []

    # =========================
    # 🔥 WRITE LOOP
    # =========================
    for idx, f in enumerate(files):

        # 🔥 FULL STRUCTURE LOG (NEW)
        print(f"SENDING: {{'step': 'file_raw', 'index': {idx}, 'keys': {list(f.keys()) if isinstance(f, dict) else 'invalid'}}}")

        if not isinstance(f, dict):
            print(f"SENDING: {{'step': 'file_invalid_structure', 'index': {idx}}}")
            errors.append(f"Not dict: {f}")
            continue

        filename = f.get("filename")
        content = f.get("content")

        # 🔥 VALIDATION
        if not isinstance(filename, str) or not filename.strip():
            print(f"SENDING: {{'step': 'invalid_filename', 'index': {idx}, 'value': '{filename}'}}")
            errors.append(f"Invalid filename: {f}")
            continue

        if not isinstance(content, str):
            print(f"SENDING: {{'step': 'invalid_content', 'file': '{filename}'}}")
            errors.append(f"Invalid content: {f}")
            continue

        filename = filename.strip()
        path = os.path.join(output_dir, filename)

        try:
            existing_content = None
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    existing_content = file.read()

            new_size = len(content)
            old_size = len(existing_content) if existing_content else 0

            print(f"SENDING: {{'step': 'file_compare', 'file': '{filename}', 'old_size': {old_size}, 'new_size': {new_size}}}")

            if existing_content == content:
                print(f"SENDING: {{'step': 'file_unchanged', 'file': '{filename}'}}")
                unchanged_files.append(filename)
            else:
                print(f"SENDING: {{'step': 'file_write', 'file': '{filename}'}}")
                changed_files.append(filename)

            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

            valid_count += 1

        except Exception as e:
            print(f"SENDING: {{'step': 'file_write_error', 'file': '{filename}', 'error': '{str(e)}'}}")
            errors.append(f"{filename}: {str(e)}")

    # =========================
    # 🔥 SANITY CHECK (NEW)
    # =========================
    if valid_count != len(files):
        print(f"SENDING: {{'step': 'partial_write_warning', 'valid': {valid_count}, 'total': {len(files)}}}")

    # =========================
    # 🔥 SUMMARY LOG
    # =========================
    print(
        f"SENDING: {{'step': 'write_summary', "
        f"'written': {valid_count}, "
        f"'changed': {len(changed_files)}, "
        f"'unchanged': {len(unchanged_files)}, "
        f"'errors': {len(errors)}}}"
    )

    # =========================
    # 🔥 FINAL RESULT
    # =========================
    if valid_count == 0:
        return {
            "success": False,
            "error": f"No valid files written. Errors: {errors}"
        }

    return {
        "success": True,
        "count": valid_count,
        "changed_files": changed_files,
        "unchanged_files": unchanged_files,
        "errors": errors if errors else None
    }
