import re


# =========================================================
# SECTION SPLITTING
# =========================================================
def split_sections(text):

    if not text:
        return []

    # 🔥 non-capturing group fix
    sections = re.split(
        r"\n\d+(?:\.\d+)*\s",
        text
    )

    cleaned = []

    for s in sections:

        if not s:
            continue

        if not isinstance(s, str):
            continue

        s = s.strip()

        if len(s) < 100:
            continue

        cleaned.append(s)

    return cleaned


# =========================================================
# SEMANTIC CHUNKING
# =========================================================
def chunk_text(text):

    sections = split_sections(text)

    chunks = []

    for sec_id, sec in enumerate(sections):

        paragraphs = sec.split("\n")

        current = ""

        for p in paragraphs:

            p = p.strip()

            if len(p) < 40:
                continue

            # 🔥 semantic chunk limit
            if len(current) + len(p) > 1200:

                chunks.append({
                    "section_id": sec_id,
                    "text": current
                })

                current = p

            else:
                current += "\n" + p

        if current:

            chunks.append({
                "section_id": sec_id,
                "text": current
            })

    return chunks
