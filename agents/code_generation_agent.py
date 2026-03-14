from services.llm_service import llm

def generate_code(spec):

    prompt = f"""
    Generate production quality C++ code for the requirement below.
    
    Return ONLY valid JSON in this format:
    
    {{
     "files":[
       {{"filename":"module.h","content":"header file"}},
       {{"filename":"module.cpp","content":"implementation"}},
       {{"filename":"test_module.cpp","content":"unit tests"}}
     ]
    }}

    Requirement:
    {spec}
    """

    response = llm.invoke(prompt)

    return response.content

