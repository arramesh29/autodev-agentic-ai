import os
from pypdf import PdfReader


def parse_pdf(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text


def collect_documents(base_folder):

    docs = []

    for root, _, files in os.walk(base_folder):

        for file in files:

            if file.lower().endswith(".pdf"):

                full_path = os.path.join(root, file)

                try:
                    text = parse_pdf(full_path)

                    docs.append({
                        "path": full_path,
                        "filename": file,
                        "text": text
                    })

                    print(f"✅ Parsed: {file}")

                except Exception as e:
                    print(f"❌ Failed: {file} → {e}")

    return docs