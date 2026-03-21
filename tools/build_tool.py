import subprocess
import os
import shutil

def build_project():

    source_dir = os.path.abspath("generated")
    build_dir = os.path.join(source_dir, "build")

    # Clean build directory
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(build_dir, exist_ok=True)

    # Configure with MSVC
    configure = subprocess.run(
        ["cmake", "-G", "NMake Makefiles", "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", source_dir],
        cwd=build_dir,
        capture_output=True,
        text=True,
        shell=True
    )

    if configure.returncode != 0:
        return configure.stdout + configure.stderr

    # Build
    build = subprocess.run(
        ["cmake", "--build", "."],
        cwd=build_dir,
        capture_output=True,
        text=True,
        shell=True
    )

    if build.returncode != 0:
        return build.stdout + build.stderr

    # ✅ Run tests
    test = subprocess.run(
        ["ctest", "--output-on-failure"],
        cwd=build_dir,
        capture_output=True,
        text=True,
        shell=True
    )

    return test.stdout + test.stderr
