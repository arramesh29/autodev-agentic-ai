import os

def write_files(files):

    os.makedirs("generated", exist_ok=True)

    for f in files:
        path = os.path.join("generated", f["filename"])

        with open(path, "w") as file:
            file.write(f["content"])
