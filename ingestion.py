from pathlib import Path
import json
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

CACHE_DIR = Path("C:/Users/ASUS/.cache/huggingface/hub")
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)

DATA_PATH = Path("data/raw")
CHROMA_PATH = Path("chroma_db")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    cache_folder=str(CACHE_DIR),
    encode_kwargs={'normalize_embeddings': True}
)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)


def load_json_files():
    docs = []
    for json_path in DATA_PATH.glob("*.json"):
        if json_path.name == "pdf_chunks.json":
            continue
        try:
            with open(json_path, encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                continue

            if content.startswith('['):
                data = json.loads(content)
            elif content.startswith('{'):
                data = json.loads(content)
                data = [data]
            else:
                lines = content.split('\n')
                data = []
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith('{') or line.startswith('[')):
                        try:
                            item = json.loads(line)
                            if isinstance(item, list):
                                data.extend(item)
                            else:
                                data.append(item)
                        except:
                            continue

            for item in data:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or item.get("description") or str(item)
                    if text and len(str(text)) > 20:
                        docs.append(Document(
                            page_content=str(text)[:2000],
                            metadata={"source": json_path.name}
                        ))
                elif isinstance(item, str) and len(item) > 20:
                    docs.append(Document(
                        page_content=item[:2000],
                        metadata={"source": json_path.name}
                    ))

            print(f"Loaded {len(docs)} items from {json_path.name}")
        except Exception as e:
            print(f"Error loading {json_path.name}: {e}")

    return docs


def load_pdf_chunks():
    docs = []
    pdf_json = DATA_PATH / "pdf_chunks.json"
    if pdf_json.exists():
        try:
            with open(pdf_json, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            text = item.get("text") or item.get("content") or str(item)
                            if text and len(str(text)) > 20:
                                docs.append(Document(
                                    page_content=str(text)[:2000],
                                    metadata=item.get("metadata", {})
                                ))
            print(f"Loaded {len(docs)} PDF chunks")
        except Exception as e:
            print(f"Error loading PDF chunks: {e}")
    return docs


def load_text_files():
    docs = []
    for txt_path in DATA_PATH.glob("*.txt"):
        try:
            with open(txt_path, encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    docs.append(Document(
                        page_content=content,
                        metadata={"source": txt_path.name, "type": "text"}
                    ))
            print(f"Loaded {txt_path.name}")
        except Exception as e:
            print(f"Error loading {txt_path.name}: {e}")
    return docs


def ingest_all():
    all_docs = []
    all_docs.extend(load_pdf_chunks())
    all_docs.extend(load_json_files())
    all_docs.extend(load_text_files())

    print(f"\nTotal documents: {len(all_docs)}")

    if not all_docs:
        print("No documents found")
        return

    splits = text_splitter.split_documents(all_docs)
    print(f"Created {len(splits)} chunks")

    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH)
    )

    print(f"Done! {len(splits)} chunks saved")


if __name__ == "__main__":
    ingest_all()