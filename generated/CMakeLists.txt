
cmake_minimum_required(VERSION 3.14)
project(GeneratedProject)

set(CMAKE_CXX_STANDARD 17)

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
    aeb_controller.cpp test_aeb_controller.cpp
)

# Link GoogleTest
target_link_libraries(test_runner gtest_main)

include(GoogleTest)
gtest_discover_tests(test_runner)
