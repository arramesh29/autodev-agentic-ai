import os
from datetime import datetime


def build_metadata(doc, chunk, chunk_id):

    filename = doc["filename"]

    lower = filename.lower()

    if "ais" in lower:
        doc_type = "regulation"

    elif "spice" in lower:
        doc_type = "process"

    else:
        doc_type = "spec"

    return {
        "source_file": filename,
        "source_path": doc["path"],
        "document_type": doc_type,
        "chunk_id": chunk_id,
        "section_id": chunk["section_id"],
        "timestamp": str(datetime.now())
    }