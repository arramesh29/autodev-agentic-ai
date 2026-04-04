import os


def write_files(files):

    os.makedirs("generated", exist_ok=True)

    # 🔥 NORMALIZE
    if isinstance(files, dict):
        files = [files]

    if not isinstance(files, list):
        print("⚠️ Invalid files input, skipping write")
        return

    valid_count = 0

    for f in files:

        if not isinstance(f, dict):
            print("⚠️ Skipping invalid file (not dict):", f)
            continue

        filename = f.get("filename")
        content = f.get("content")

        # 🔥 STRICT BUT SAFE VALIDATION
        if not filename or not isinstance(filename, str):
            print("⚠️ Invalid filename, skipping")
            continue

        if content is None or not isinstance(content, str):
            print("⚠️ Invalid content, skipping")
            continue

        path = os.path.join("generated", filename)

        try:
            with open(path, "w") as file:
                file.write(content)
            valid_count += 1
        except Exception as e:
            print("⚠️ Failed writing file:", e)

    # 🔥 CRITICAL CHANGE: DO NOT CRASH
    if valid_count == 0:
        print("⚠️ No valid files written — continuing without crash")
