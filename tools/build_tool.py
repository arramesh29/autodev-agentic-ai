import subprocess
import os

def build_project():

    os.chdir("generated")

    result = subprocess.run(
        ["cmake", "--build", "."],
        capture_output=True,
        text=True
    )

    return result.stdout + result.stderr
