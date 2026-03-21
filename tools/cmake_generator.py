import os

def generate_cmake(files):

    cpp_files = []
    test_files = []

    for f in files:
        name = f["filename"]

        if name.endswith(".cpp") and "test" not in name:
            cpp_files.append(name)

        if "test" in name:
            test_files.append(name)

    cmake_content = f"""
cmake_minimum_required(VERSION 3.14...4.0)
project(GeneratedProject)

set(CMAKE_CXX_STANDARD 17)

# Force consistent runtime
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDebugDLL")

# Enable testing
enable_testing()

# Fetch GoogleTest
include(FetchContent)

FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/heads/main.zip
)

FetchContent_MakeAvailable(googletest)

# Add executable
add_executable(test_runner
    {" ".join(cpp_files + test_files)}
)

# Link GoogleTest
target_link_libraries(test_runner gtest_main)

include(GoogleTest)
gtest_discover_tests(test_runner)
"""

    os.makedirs("generated", exist_ok=True)

    with open("generated/CMakeLists.txt", "w") as f:
        f.write(cmake_content)
