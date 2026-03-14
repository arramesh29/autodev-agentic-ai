from services.llm_service import llm

def create_plan(requirement):

    prompt = f"""
    Break the following automotive requirement into
    software development tasks:

    {requirement}
    """

    response = llm.invoke(prompt)

    return response.content
