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

                ┌─────────────────────────────┐
                │        FastAPI API          │
                │     (/generate endpoint)    │
                └─────────────┬───────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │   Development Workflow      │
                │ (Langfuse Observability)    │
                └─────────────┬───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Planner Agent │   │ Code Gen Agent   │   │  Debug Agent     │
│ (LLM)         │   │ (LLM → C++ code) │   │ (Fix failures)   │
└───────────────┘   └──────────────────┘   └──────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │         Tools Layer         │
                │-----------------------------│
                │ file_writer                 │
                │ cmake_generator             │
                │ build_tool (CMake + CTest)  │
                │ test_parser                 │
                │ confidence_scorer           │
                └─────────────┬───────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │   C++ Build System          │
                │  (MSVC + CMake + GTest)     │
                └─────────────┬───────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │   Test Results + Logs       │
                └─────────────┬───────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │ Confidence + Decision Logic │
                │  (Retry / Fix / Success)    │
                └─────────────────────────────┘

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
