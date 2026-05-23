from sentence_transformers import CrossEncoder

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank(query, docs):

    if not docs:
        return []

    pairs = [
        [query, d["text"]]
        for d in docs
    ]

    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(scores, docs),
        reverse=True,
        key=lambda x: x[0]
    )

    return [r[1] for r in ranked]