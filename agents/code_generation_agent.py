from services.llm_service import llm

def generate_code(spec):

    prompt = f"""
    Generate C++ code for the following automotive module:

    {spec}
    """

    response = llm.invoke(prompt)

    return response.content
