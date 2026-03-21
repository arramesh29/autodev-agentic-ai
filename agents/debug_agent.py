from services.llm_service import llm
import json

def fix_code(error_log, files):

    prompt = f"""
    You are an expert automotive C++ developer.

    The following code failed to compile.

    ERROR LOG:
    {error_log}

    FILES:
    {files}

    Fix ALL issues.

    Ensure:
    - Correct headers
    - Valid C++17
    - No syntax errors

    Return ONLY JSON:
    {{
      "files":[{{"filename":"...","content":"..."}}]
    }}
    """

    response = llm.invoke(prompt)

    text = response.content.strip()
    text = text.replace("```json", "").replace("```", "")

    return json.loads(text)["files"]
