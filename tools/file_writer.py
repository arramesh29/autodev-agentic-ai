import os
import shutil


def write_files(files):

    output_dir = "generated"

    # =========================
    # 🔥 SAFE CLEANUP (FIXED)
    # =========================
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            path = os.path.join(output_dir, item)

            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)  # 🔥 handles /bin
            except Exception as e:
                print(f"⚠️ Cleanup skipped for {path}: {e}")

    os.makedirs(output_dir, exist_ok=True)

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
    # 🔥 WRITE LOOP (FIXED)
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
    # 🔥 FINAL RESULT (FIXED)
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
