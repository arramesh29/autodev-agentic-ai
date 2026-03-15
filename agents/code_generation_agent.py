from services.llm_service import llm
import json

def generate_code(spec):

    prompt = f"""
    You are an automotive software engineer.

    Generate C++ implementation and tests for the requirement below.

    Return ONLY valid JSON.
    Do not include explanations.
    Do not include markdown.

    Format:

    {{
      "files":[
        {{"filename":"module.h","content":"header code"}},
        {{"filename":"module.cpp","content":"implementation"}},
        {{"filename":"test_module.cpp","content":"unit tests"}}
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

