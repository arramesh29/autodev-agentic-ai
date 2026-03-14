import subprocess

def run_static_analysis(file):

    result = subprocess.run(
        ["clang-tidy", file],
        capture_output=True,
        text=True
    )

    return result.stdout
