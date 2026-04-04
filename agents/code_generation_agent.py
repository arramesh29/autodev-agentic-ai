from services.llm_service import llm
import json
import re


def generate_code(spec, trace=None, parent_span=None):

    # SAFE span creation
    span = None
    if trace:
        span = (
            parent_span.span(name="generate_code_agent")
            if parent_span
            else trace.span(name="generate_code_agent")
        )

    prompt = f"""
You are an automotive C++ software engineer.
Generate production-grade C++ code and unit tests using GoogleTest.

Requirements:
- Follow modular design (.h + .cpp)
- No experimental code
- Deterministic logic (no randomness)
- Automotive safety style (clear logic, no undefined behavior)

IMPORTANT:
    - Include all necessary headers
    - Use standard C++ includes
    - Ensure code compiles without errors
    - Avoid missing includes (e.g., <limits>, <cmath>, <vector>)

Unit Test Requirements:
- Use GoogleTest
- Cover:
  - C0 (statement coverage)
  - C1 (branch coverage)
- Include:
  - normal cases
  - boundary conditions
  - failure conditions
  - edge cases

Return ONLY valid JSON.

STRICT RULES:
- "files" MUST be a list
- Each item MUST be an object with:
    - "filename": string
    - "content": string
- DO NOT return raw strings inside "files"
- DO NOT return empty list
- DO NOT omit filename or content

INVALID examples (DO NOT DO):
"files": ["some code"]
"files": "string"
"files": []

VALID example:
"files": [
  {{"filename": "a.h", "content": "..."}},
  {{"filename": "a.cpp", "content": "..."}}
]

Format:

{{
  "files":[
    {{"filename":"aeb_controller.h","content":"header code"}},
    {{"filename":"aeb_controller.cpp","content":"implementation"}},
    {{"filename":"test_aeb_controller.cpp","content":"GoogleTest code"}}
  ]
}}

Requirement:
{spec}
"""

    generation = None
    text = None

    try:
        # Langfuse generation
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

        # extract JSON block if extra text exists
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output")

        json_str = match.group(0)

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
