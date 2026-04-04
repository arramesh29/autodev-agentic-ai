import os


def write_files(files):

    os.makedirs("generated", exist_ok=True)

    if not isinstance(files, list):
        raise ValueError(f"Expected list of files, got {type(files)}")

    for f in files:

        # 🔥 CRITICAL VALIDATION
        if not isinstance(f, dict):
            print("⚠️ Skipping invalid file (not dict):", type(f))
            continue

        if "filename" not in f or "content" not in f:
            print("⚠️ Skipping invalid file structure:", f)
            continue

        path = os.path.join("generated", f["filename"])

        with open(path, "w") as file:
            file.write(f["content"])
