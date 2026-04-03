from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler

import os
from dotenv import load_dotenv

load_dotenv()


# Create Langfuse callback handler (GLOBAL)
langfuse_handler = CallbackHandler(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)


# Initialize LLM with callback
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    callbacks=[langfuse_handler]
)
