import os


def write_files(files):

    os.makedirs("generated", exist_ok=True)

    # 🔥 STRICT INPUT VALIDATION
    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        raise ValueError(f"Invalid files input type: {type(files)}")

    valid_count = 0
    errors = []

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

        path = os.path.join("generated", filename.strip())

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            valid_count += 1

        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    # 🔥 HARD FAIL (MANDATORY)
    if valid_count == 0:
        raise ValueError(
            "🚨 CRITICAL: No valid files written.\n"
            f"Errors: {errors}"
        )

    return valid_count
