import os


def write_files(files):

    output_dir = "generated"
    os.makedirs(output_dir, exist_ok=True)

    # 🔥 ENTRY LOG (CRITICAL)
    print(f"SENDING: {{'step': 'write_files_called', 'file_count': {len(files) if isinstance(files, list) else 'invalid'}}}")

    # =========================
    # 🔥 INPUT VALIDATION
    # =========================
    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        print("SENDING: {'step': 'write_error', 'message': 'Invalid files input'}")
        return {
            "success": False,
            "error": f"Invalid files input type: {type(files)}"
        }

    valid_count = 0
    errors = []
    changed_files = []
    unchanged_files = []

    # =========================
    # 🔥 WRITE LOOP
    # =========================
    for f in files:

        if not isinstance(f, dict):
            errors.append(f"Not dict: {f}")
            continue

        filename = f.get("filename")
        content = f.get("content")

        if not isinstance(filename, str) or not filename.strip():
            errors.append(f"Invalid filename: {f}")
            continue

        if not isinstance(content, str):
            errors.append(f"Invalid content: {f}")
            continue

        filename = filename.strip()
        path = os.path.join(output_dir, filename)

        try:
            # 🔥 READ EXISTING CONTENT
            existing_content = None
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    existing_content = file.read()

            # 🔥 CHANGE DETECTION
            if existing_content == content:
                print(f"SENDING: {{'step': 'file_unchanged', 'file': '{filename}'}}")
                unchanged_files.append(filename)
            else:
                print(f"SENDING: {{'step': 'file_write', 'file': '{filename}'}}")
                changed_files.append(filename)

            # 🔥 ALWAYS WRITE (NO SKIP)
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

            valid_count += 1

        except Exception as e:
            print(f"SENDING: {{'step': 'file_write_error', 'file': '{filename}', 'error': '{str(e)}'}}")
            errors.append(f"{filename}: {str(e)}")

    # =========================
    # 🔥 SUMMARY LOG
    # =========================
    print(f"SENDING: {{'step': 'write_summary', 'written': {valid_count}, 'changed': {len(changed_files)}, 'unchanged': {len(unchanged_files)}}}")

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
