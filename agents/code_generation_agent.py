from services.llm_service import llm
import json

def generate_code(spec):

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
    Do not include explanations.
    Do not include markdown.

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

    response = llm.invoke(prompt)
    text = response.content.strip()

    # Remove markdown if present
    text = text.replace("```json", "")
    text = text.replace("```", "")

    try:
        result = json.loads(text)
    except Exception:
        raise ValueError(f"Invalid JSON from LLM:\n{text}")

    return result

