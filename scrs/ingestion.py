from pathlib import Path
import json
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# تنظیم مسیر کش
CACHE_DIR = Path("C:/Users/ASUS/.cache/huggingface/hub")
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)

DATA_PATH = Path("data/raw")
CHROMA_PATH = Path("chroma_db")

# Embedding
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    cache_folder=str(CACHE_DIR),
    encode_kwargs={'normalize_embeddings': True}
)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)


def ingest_all():
    all_docs = []

    # خواندن فایل json
    json_path = DATA_PATH / "messages.json"
    if not json_path.exists():
        json_path = DATA_PATH / "messages_backup.json"

    if json_path.exists():
        print(f"📄 در حال خواندن: {json_path.name}")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        for msg in data:
            if isinstance(msg, dict) and msg.get("text"):
                doc = Document(
                    page_content=msg["text"],
                    metadata={"source": "telegram", "type": "text"}
                )
                all_docs.append(doc)

    # خواندن فایل‌های متنی
    for txt_path in DATA_PATH.glob("*.txt"):
        print(f"📄 در حال خواندن: {txt_path.name}")
        with open(txt_path, encoding="utf-8") as f:
            content = f.read()
            doc = Document(
                page_content=content,
                metadata={"source": txt_path.name, "type": "text"}
            )
            all_docs.append(doc)

    print(f"تعداد اسناد پیدا شده: {len(all_docs)}")

    if not all_docs:
        print("❌ فایلی پیدا نشد")
        return

    splits = text_splitter.split_documents(all_docs)

    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH)
    )

    print(f"✅ Ingestion با موفقیت انجام شد! {len(splits)} chunk ذخیره شد.")


if __name__ == "__main__":
    ingest_all()