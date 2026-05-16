from services.llm_service import llm
import json
import re


def safe_json_extract(text):
    cleaned = text.replace("```json", "").replace("```", "")

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None

    json_str = match.group(0)

    # Fix trailing commas
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    try:
        return json.loads(json_str)
    except:
        return None


def generate_code(plan, requirements=None, trace=None, parent_span=None):

    span = None
    if trace:
        span = (
            parent_span.span(name="generate_code_agent")
            if parent_span
            else trace.span(name="generate_code_agent")
        )

    # =========================
    # REQUIREMENT CONTEXT
    # =========================
    req_context = ""
    if requirements:
        for r in requirements:
            req_context += f"{r.get('id', 'REQ-UNK')}: {r.get('description', '')}\n"

    # =========================
    # PROMPT
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

    TEST(featurename, TTC_REQ001)

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
    Derive 3-4 letter feature identifier based on the requirements and replace the "featurename" with the same while usimg the prompts below.
  1. featurename_controller.h
  2. featurename_controller.cpp
  3. test_featurename_controller.cpp

- DO NOT skip any file
- DO NOT return partial output

==============================
STRICT JSON FORMAT
==============================
{{
  "files":[
    {{"filename":"featurename_controller.h","content":"header code"}},
    {{"filename":"featurename_controller.cpp","content":"implementation"}},
    {{"filename":"test_featurename_controller.cpp","content":"GoogleTest code"}}
  ]
}}
"""

    generation = None
    text = None

    try:
        if span:
            generation = span.generation(
                name="llm_generate_code",
                model="gpt-4o",
                input=prompt
            )

        # =========================
        # 🔥 RETRY LOGIC (NEW)
        # =========================
        MAX_RETRIES = 3
        result = None

        for attempt in range(MAX_RETRIES):

            response = llm.invoke(prompt)
            text = response.content.strip()

            parsed = safe_json_extract(text)

            if parsed:
                result = parsed
                break

        if not result:
            return {
                "error": "LLM returned invalid JSON after retries",
                "raw_output": text
            }

        if generation:
            generation.end(output=text[:2000])

        # =========================
        # 🔥 NORMALIZATION
        # =========================
        files = result.get("files", [])

        if isinstance(files, dict):
            files = [files]

        if not isinstance(files, list):
            return {"error": "files must be list", "raw_output": text}

        validated_files = [
            f for f in files
            if isinstance(f, dict)
            and "filename" in f
            and "content" in f
        ]

        if not validated_files:
            return {"error": "No valid files returned", "raw_output": text}

        # =========================
        # REQUIRED FILE CHECK
        # =========================
        # 🔥 GENERIC FILE VALIDATION (FIXED)
        
        filenames = [f["filename"] for f in validated_files]
        
        header = any(fn.endswith("_controller.h") for fn in filenames)
        impl = any(fn.endswith("_controller.cpp") and not fn.startswith("test_") for fn in filenames)
        test = any(fn.startswith("test_") and fn.endswith("_controller.cpp") for fn in filenames)
        
        if not (header and impl and test):
            return {
                "error": "Missing required file types (header / impl / test)",
                "raw_output": text,
                "returned_files": filenames
            }

        # =========================
        # TRACEABILITY CHECK
        # =========================
        if requirements:
            for f in validated_files:
                if "REQ-" not in f["content"]:
                    return {
                        "error": f"Missing REQ traceability in {f['filename']}",
                        "raw_output": text
                    }

        result["files"] = validated_files

        if span:
            span.end(output={"file_count": len(validated_files)})

        return result

    except Exception as e:

        if generation:
            generation.end(
                level="ERROR",
                status_message=str(e),
                metadata={"raw_response": text[:2000] if text else "no response"}
            )

        if span:
            span.end(level="ERROR", status_message=str(e))

        # 🔥 DO NOT CRASH PIPELINE
        return {
            "error": str(e),
            "raw_output": text if text else "no response"
        }
