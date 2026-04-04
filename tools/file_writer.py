import os


def write_files(files):

    os.makedirs("generated", exist_ok=True)

    # 🔥 NORMALIZE INPUT HERE (FINAL SAFETY LAYER)
    if isinstance(files, dict):
        files = [files]

    elif isinstance(files, str):
        raise ValueError("write_files received string instead of file structure")

    elif not isinstance(files, list):
        raise ValueError(f"Expected list/dict, got {type(files)}")

    # 🔥 VALIDATE + WRITE
    valid_count = 0

    for f in files:

        if not isinstance(f, dict):
            print("⚠️ Skipping invalid file (not dict):", type(f))
            continue

        if "filename" not in f or "content" not in f:
            print("⚠️ Skipping invalid file structure:", f)
            continue

        path = os.path.join("generated", f["filename"])

        with open(path, "w") as file:
            file.write(f["content"])

        valid_count += 1

    if valid_count == 0:
        raise ValueError("No valid files to write")
