import re


def split_sections(text):

    sections = re.split(r"\n\d+(\.\d+)*\s", text)

    return [s.strip() for s in sections if len(s.strip()) > 100]


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