import subprocess
import os

import subprocess
import os
import shutil

def build_project():

    source_dir = os.path.abspath("generated")
    build_dir = os.path.join(source_dir, "build")

    # 🔥 Clean build directory completely (safe & simple)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(build_dir, exist_ok=True)

    # Step 1: Configure
    configure = subprocess.run(
        ["cmake", "-G", "Visual Studio 17 2022", source_dir],
        cwd=build_dir,
        capture_output=True,
        text=True
    )

    if configure.returncode != 0:
        return configure.stdout + configure.stderr

    # Step 2: Build
    build = subprocess.run(
        ["cmake", "--build", ".", "--config", "Release"],
        cwd=build_dir,
        capture_output=True,
        text=True
    )

    return build.stdout + build.stderr
