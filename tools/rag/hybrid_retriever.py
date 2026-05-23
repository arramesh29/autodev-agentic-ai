from rank_bm25 import BM25Okapi
from tools.rag.rag_store import search


def hybrid_search(query, top_k=5):

    vector_results = search(query, top_k=top_k * 3)

    if not vector_results:
        return []

    corpus = [r["text"].split() for r in vector_results]

    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(query.split())

    ranked = sorted(
        zip(scores, vector_results),
        reverse=True,
        key=lambda x: x[0]
    )

    return [r[1] for r in ranked[:top_k]]