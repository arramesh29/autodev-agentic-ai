def build_context(docs, max_chars=5000):

    context = ""

    total = 0

    for d in docs:

        text = d["text"]

        if total + len(text) > max_chars:
            break

        meta = d["metadata"]

        context += f"""
SOURCE: {meta.get('source_file')}
TYPE: {meta.get('document_type')}

{text}

-----------------------------------
"""

        total += len(text)

    return context