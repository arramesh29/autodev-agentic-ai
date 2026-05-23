from tools.rag.hybrid_retriever import hybrid_search
from tools.rag.context_builder import build_context


def retrieve_context(query, agent_type):

    docs = hybrid_search(query)

    context = build_context(docs)

    return context
