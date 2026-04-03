from langchain_openai import ChatOpenAI
from langfuse import Langfuse

import os
from dotenv import load_dotenv

import atexit

atexit.register(langfuse.flush)

load_dotenv()

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL")
)

print("LANGFUSE_PUBLIC_KEY:", os.getenv("LANGFUSE_PUBLIC_KEY"))
print("LANGFUSE_SECRET_KEY:", os.getenv("LANGFUSE_SECRET_KEY"))
print("LANGFUSE_HOST:", os.getenv("LANGFUSE_BASE_URL"))

# Plain LLM (no callbacks anymore)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0
)
