import subprocess
import os

def build_project():

    build_dir = "generated"

    # Configure with Visual Studio generator
    configure = subprocess.run(
        ["cmake", "-G", "Visual Studio 17 2022", "."],
        cwd=build_dir,
        capture_output=True,
        text=True
    )

    if configure.returncode != 0:
        return configure.stdout + configure.stderr

    # Build
    build = subprocess.run(
        ["cmake", "--build", ".", "--config", "Release"],
        cwd=build_dir,
        capture_output=True,
        text=True
    )

    return build.stdout + build.stderr
