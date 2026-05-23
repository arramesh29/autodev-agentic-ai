import faiss
import json
import os
import numpy as np

from fastembed import TextEmbedding

# =========================================================
# 🔥 FASTEMBED MODEL (NO TORCH)
# =========================================================
embedding_model = TextEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

DIM = 384

INDEX_PATH = "rag_data/vector.index"
META_PATH = "rag_data/metadata.json"

os.makedirs("rag_data", exist_ok=True)

# =========================================================
# LOAD / CREATE INDEX
# =========================================================
if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
else:
    index = faiss.IndexFlatIP(DIM)

# =========================================================
# LOAD / CREATE METADATA
# =========================================================
if os.path.exists(META_PATH):

    with open(META_PATH, "r", encoding="utf-8") as f:
        METADATA = json.load(f)

else:
    METADATA = []


# =========================================================
# EMBEDDING
# =========================================================
def embed(text: str):

    embeddings = list(
        embedding_model.embed([text])
    )

    vec = np.array([embeddings[0]]).astype("float32")

    return vec


# =========================================================
# ADD DOCUMENT
# =========================================================
def add_document(text, metadata):

    vector = embed(text)

    index.add(vector)

    METADATA.append({
        "text": text,
        "metadata": metadata
    })


# =========================================================
# SAVE INDEX
# =========================================================
def save():

    faiss.write_index(index, INDEX_PATH)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(METADATA, f, indent=2)


# =========================================================
# SEARCH
# =========================================================
def search(query, top_k=10):

    if len(METADATA) == 0:
        return []

    q = embed(query)

    scores, indices = index.search(q, top_k)

    results = []

    for idx in indices[0]:

        if idx >= len(METADATA):
            continue

        results.append(METADATA[idx])

    return results
