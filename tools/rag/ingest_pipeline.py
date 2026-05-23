from tools.rag.document_parser import collect_documents
from tools.rag.chunker import chunk_text
from tools.rag.metadata_manager import build_metadata
from tools.rag.rag_store import add_document, save


BASE_FOLDER = r"C:\Ramesh_HigherStudies\Project\Standards_Legislations"


def ingest_all_documents():

    docs = collect_documents(BASE_FOLDER)

    total_chunks = 0

    for doc in docs:

        chunks = chunk_text(doc["text"])

        for chunk_id, chunk in enumerate(chunks):

            metadata = build_metadata(
                doc,
                chunk,
                chunk_id
            )

            add_document(
                chunk["text"],
                metadata
            )

            total_chunks += 1

    save()

    print(f"✅ Total chunks indexed: {total_chunks}")