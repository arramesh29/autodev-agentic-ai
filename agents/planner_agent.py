from services.llm_service import llm

def create_plan(requirement):

    prompt = f"""
    Break the following automotive software requirement
    into development steps:

    {requirement}
    """

    return llm.predict(prompt)
