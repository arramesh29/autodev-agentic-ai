from services.llm_service import llm
import json


def fix_code(error_log, files):
    prompt = f"""
You are a senior automotive C++ software engineer.

The system failed during build or test execution.

ERROR / TEST OUTPUT:
{error_log}

FILES:
{files}

Instructions:
- Fix compilation errors if present
- Fix failing test logic if present
- Do NOT hardcode values just to pass tests
- Maintain clean, production-quality C++ code
- Ensure proper includes and correct formulas

Return ONLY valid JSON:
{{
  "files":[{{"filename":"...","content":"..."}}]
}}
"""

    response = llm.invoke(prompt)

    text = response.content.strip()
    text = text.replace("```json", "").replace("```", "")

    return json.loads(text)["files"]
