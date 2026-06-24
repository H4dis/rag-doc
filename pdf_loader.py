from pathlib import Path
import json
import os
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

DATA_PATH = Path("data/raw/documents")
OUTPUT_PATH = DATA_PATH.parent / "pdf_chunks.json"


def detect_pdf_loader(pdf_path):
    try:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        if pages and any(p.page_content.strip() for p in pages):
            return pages, "PyPDFLoader"
    except:
        pass

    try:
        loader = UnstructuredPDFLoader(str(pdf_path))
        pages = loader.load()
        if pages and any(p.page_content.strip() for p in pages):
            return pages, "UnstructuredPDFLoader"
    except:
        pass

    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        if text.strip():
            return [Document(page_content=text, metadata={"source": pdf_path.name})], "pdfplumber"
    except:
        pass

    try:
        from pypdf import PdfReader
        text = ""
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        if text.strip():
            return [Document(page_content=text, metadata={"source": pdf_path.name})], "pypdf"
    except:
        pass

    return [], "None"


def load_all_pdfs():
    all_docs = []
    pdf_files = list(DATA_PATH.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {DATA_PATH}")
        return []

    print(f"Found {len(pdf_files)} PDF files")

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")

        pages, method = detect_pdf_loader(pdf_path)

        if pages:
            print(f"  Success with {method} - {len(pages)} pages")
            all_docs.extend(pages)
        else:
            print(f"  Failed to extract text")

    if not all_docs:
        print("No text could be extracted from any PDF")
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100
    )

    chunks = text_splitter.split_documents(all_docs)

    chunks_data = []
    for chunk in chunks:
        chunks_data.append({
            "text": chunk.page_content,
            "metadata": chunk.metadata
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    print(f"Created {len(chunks)} chunks")
    print(f"Saved to {OUTPUT_PATH}")

    return chunks


if __name__ == "__main__":
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    load_all_pdfs()