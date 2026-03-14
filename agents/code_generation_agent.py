from services.llm_service import llm

def generate_code(spec):

    prompt = f"""
    Generate production quality C code
    for this automotive module:

    {spec}
    """

    return llm.predict(prompt)
