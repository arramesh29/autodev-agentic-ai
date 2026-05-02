from services.llm_service import llm
import json
import re


def generate_code(plan, requirements=None, trace=None, parent_span=None):

    # =========================
    # SAFE span creation
    # =========================
    span = None
    if trace:
        span = (
            parent_span.span(name="generate_code_agent")
            if parent_span
            else trace.span(name="generate_code_agent")
        )

    # =========================
    # 🔧 REQUIREMENT CONTEXT (NEW)
    # =========================
    req_context = ""

    if requirements:
        for r in requirements:
            req_context += f"{r.get('id', 'REQ-UNK')}: {r.get('description', '')}\n"

    # =========================
    # 🧠 ENHANCED PROMPT
    # =========================
    prompt = f"""
You are an automotive C++ software engineer.

Generate production-grade C++ code and unit tests using GoogleTest.

==============================
REQUIREMENTS (TRACEABLE)
==============================
{req_context if requirements else "No structured requirements provided"}

==============================
DEVELOPMENT PLAN
==============================
{plan}

==============================
CRITICAL TRACEABILITY RULE
==============================
- Every function MUST include REQ-ID in comments
- Every test MUST reference REQ-ID
- Maintain mapping:
    REQ → Function → Test

Example:
    // REQ-001: TTC calculation
    float compute_ttc(...)

    TEST(AEB, TTC_REQ001)

==============================
GENERAL RULES
==============================
- Modular design (.h + .cpp)
- Deterministic logic (no randomness)
- Automotive safety style
- No undefined behavior
- Include ALL necessary headers
- Code MUST compile

==============================
UNIT TEST RULES
==============================
- Use GoogleTest
- Cover:
  - normal cases
  - boundary conditions
  - failure conditions
  - edge cases

==============================
🚨 CRITICAL OUTPUT RULES
==============================
- MUST generate ALL 3 files:
  1. aeb_controller.h
  2. aeb_controller.cpp
  3. test_aeb_controller.cpp

- DO NOT skip any file
- DO NOT return partial output

==============================
STRICT JSON FORMAT
==============================
{{
  "files":[
    {{"filename":"aeb_controller.h","content":"header code"}},
    {{"filename":"aeb_controller.cpp","content":"implementation"}},
    {{"filename":"test_aeb_controller.cpp","content":"GoogleTest code"}}
  ]
}}
"""

    generation = None
    text = None

    try:
        # =========================
        # Langfuse generation
        # =========================
        if span:
            generation = span.generation(
                name="llm_generate_code",
                model="gpt-4o",
                input=prompt
            )

        response = llm.invoke(prompt)
        text = response.content.strip()

        if generation:
            generation.end(output=text[:2000])

        # =========================
        # 🔥 SAFE JSON EXTRACTION
        # =========================
        cleaned = text.replace("```json", "").replace("```", "")

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output")

        json_str = match.group(0)

        # Cleanup trailing commas
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        result = json.loads(json_str)

        # =========================
        # 🔥 NORMALIZATION
        # =========================
        files = result.get("files", [])

        if isinstance(files, dict):
            files = [files]

        if not isinstance(files, list):
            raise ValueError("files must be a list")

        # =========================
        # 🔥 VALIDATION
        # =========================
        validated_files = []
        for f in files:
            if isinstance(f, dict) and "filename" in f and "content" in f:
                validated_files.append(f)

        if not validated_files:
            raise ValueError("No valid files returned from LLM")

        # =========================
        # 🔥 ENFORCE REQUIRED FILES
        # =========================
        required_files = {
            "aeb_controller.h",
            "aeb_controller.cpp",
            "test_aeb_controller.cpp"
        }

        returned_files = set(f["filename"] for f in validated_files)

        missing_files = required_files - returned_files

        if missing_files:
            raise ValueError(f"Missing required files from LLM: {missing_files}")

        # =========================
        # 🔥 TRACEABILITY CHECK (NEW)
        # =========================
        if requirements:
            for f in validated_files:
                if "REQ-" not in f["content"]:
                    raise ValueError(
                        f"Missing REQ-ID traceability in file: {f['filename']}"
                    )

        result["files"] = validated_files

        # =========================
        # Langfuse span end
        # =========================
        if span:
            span.end(
                output={
                    "file_count": len(validated_files)
                }
            )

        return result

    except Exception as e:

        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={
                    "raw_response": text[:2000] if text else "no response"
                }
            )

        if span:
            span.end(
                level="ERROR",
                status_message=str(e)
            )

        raise ValueError(
            f"Invalid JSON from LLM:\n{text if text else 'No response'}"
        )
