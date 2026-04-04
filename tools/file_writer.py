import os


def write_files(files):

    output_dir = "generated"

    os.makedirs(output_dir, exist_ok=True)

    # =========================
    # 🔥 SAFE CLEANUP (SOURCE ONLY)
    # =========================
    for item in os.listdir(output_dir):
        path = os.path.join(output_dir, item)

        # 🚫 DO NOT DELETE build/system files
        if item.lower() == "cmakelists.txt":
            continue

    # =========================
    # 🔥 INPUT VALIDATION
    # =========================
    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        return {
            "success": False,
            "error": f"Invalid files input type: {type(files)}"
        }

    valid_count = 0
    errors = []

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

        path = os.path.join(output_dir, filename.strip())

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            valid_count += 1

        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

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
        "errors": errors if errors else None
    }
