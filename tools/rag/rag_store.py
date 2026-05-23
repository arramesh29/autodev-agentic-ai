import faiss
import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

DIM = 384

INDEX_PATH = "rag_data/vector.index"
META_PATH = "rag_data/metadata.json"

os.makedirs("rag_data", exist_ok=True)

if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
else:
    index = faiss.IndexFlatIP(DIM)

if os.path.exists(META_PATH):
    with open(META_PATH, "r", encoding="utf-8") as f:
        METADATA = json.load(f)
else:
    METADATA = []


def embed(text: str):
    vec = MODEL.encode([text])[0]
    return np.array([vec]).astype("float32")


def add_document(text, metadata):

    vector = embed(text)

    index.add(vector)

    METADATA.append({
        "text": text,
        "metadata": metadata
    })


def save():

    faiss.write_index(index, INDEX_PATH)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(METADATA, f, indent=2)


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