from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Plain LLM (no callbacks anymore)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0
)
