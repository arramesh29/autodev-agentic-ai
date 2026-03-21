import subprocess

def build_project():

    result = subprocess.run(
        ["cmake", "--build", "."],
        capture_output=True,
        text=True
    )

    return result.stdout + result.stderr
