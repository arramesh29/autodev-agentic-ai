import subprocess
import os

def build_project():

    build_dir = "generated"

    # Configure
    configure = subprocess.run(
        ["cmake", "."],
        cwd=build_dir,
        capture_output=True,
        text=True
    )

    if configure.returncode != 0:
        return configure.stdout + configure.stderr

    # Build
    build = subprocess.run(
        ["cmake", "--build", "."],
        cwd=build_dir,
        capture_output=True,
        text=True
    )

    return build.stdout + build.stderr
