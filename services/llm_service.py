from langchain_openai import ChatOpenAI
from langfuse import Langfuse

import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL")
)

# Plain LLM (no callbacks anymore)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0
)
