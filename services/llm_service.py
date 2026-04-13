from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Plain LLM (no callbacks anymore)
llm = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0
)
