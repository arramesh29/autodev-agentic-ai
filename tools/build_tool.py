import subprocess
import os
import shutil
import uuid


def build_and_test():

    # 🔥 UNIQUE BUILD ID (CRITICAL DEBUG)
    build_id = str(uuid.uuid4())[:8]
    print(f"🔥 BUILD_START id={build_id}")

    source_dir = os.path.abspath("generated")
    build_dir = os.path.abspath("../autodev_build")

    # =========================
    # 🔥 CLEAN BUILD DIR
    # =========================
    try:
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
            print(f"🔥 BUILD_CLEAN id={build_id}")
    except Exception as e:
        print(f"🔥 BUILD_CLEAN_FAILED id={build_id} error={str(e)}")

    os.makedirs(build_dir, exist_ok=True)

    # =========================
    # 🔥 CONFIGURE
    # =========================
    print(f"🔥 CONFIGURE_START id={build_id}")

    configure = subprocess.run(
        ["cmake", "-G", "NMake Makefiles", "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", source_dir],
        cwd=build_dir,
        capture_output=True,
        text=True,
        shell=True
    )

    if configure.returncode != 0:
        print(f"🔥 CONFIGURE_FAIL id={build_id}")
        return configure.stdout + configure.stderr

    print(f"🔥 CONFIGURE_OK id={build_id}")

    # =========================
    # 🔥 BUILD
    # =========================
    print(f"🔥 BUILD_STEP_START id={build_id}")

    build = subprocess.run(
        ["cmake", "--build", "."],
        cwd=build_dir,
        capture_output=True,
        text=True,
        shell=True
    )

    if build.returncode != 0:
        print(f"🔥 BUILD_FAIL id={build_id}")
        return build.stdout + build.stderr

    print(f"🔥 BUILD_OK id={build_id}")

    # =========================
    # 🔥 TEST
    # =========================
    print(f"🔥 TEST_START id={build_id}")

    test = subprocess.run(
        ["ctest", "--output-on-failure"],
        cwd=build_dir,
        capture_output=True,
        text=True,
        shell=True
    )

    print(f"🔥 TEST_COMPLETE id={build_id}")

    # =========================
    # 🔥 RETURN OUTPUT
    # =========================
    return test.stdout + test.stderr
