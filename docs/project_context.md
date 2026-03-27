# Agentic AI Automotive Development System

## Overview

System that:

* Takes automotive requirements (AEB etc.)
* Generates C++ production code
* Generates GoogleTest unit tests
* Builds using CMake
* Runs tests (CTest)
* Uses debug agent to fix failures
* Uses Langfuse for observability

## Architecture

* FastAPI (api/app.py)
* Workflow (workflows/development_workflow.py)
* Agents:

  * planner_agent
  * code_generation_agent
  * debug_agent
* Tools:

  * file_writer
  * cmake_generator
  * build_tool
  * test_parser
  * confidence_scorer

## Key Features

* Multi-step agent workflow
* Auto-debug loop (retry up to N times)
* Structured test parsing
* Confidence scoring system
* GoogleTest integration
* C0/C1 coverage goal (planned)

## Current Issues Solved

* Langchain import issues
* Langfuse API changes
* JSON parsing failures
* CMake + MSVC setup
* Runtime library conflicts
* Uvicorn reload issues with build folders
* False success detection fixed

## Current Status

* End-to-end flow working
* Build + test + debug loop functional
* Needs:

  * coverage integration
  * better debug strategies
  * architecture separation (build service)

## Tech Stack

* Python (FastAPI)
* Langchain
* Langfuse
* C++ (MSVC)
* CMake
* GoogleTest
