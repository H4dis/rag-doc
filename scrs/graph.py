from pathlib import Path
from typing import TypedDict, List
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from history import history

# ========== تنظیمات ==========
# کلید OpenRouter
os.environ["OPENROUTER_API_KEY"] = "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"

# مسیر کش HuggingFace
CACHE_DIR = Path("C:/Users/ASUS/.cache/huggingface/hub")
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)

CHROMA_PATH = Path("chroma_db")

# ========== 1. مدل Embedding (برای جستجو) ==========
print("📥 بارگذاری مدل Embedding...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    cache_folder=str(CACHE_DIR),
    encode_kwargs={'normalize_embeddings': True}
)

# ========== 2. مدل LLM (برای تولید پاسخ) ==========
print("✅ اتصال به OpenRouter...")
llm = ChatOpenRouter(
    model="openrouter/free",
    temperature=0.3,
    max_tokens=500,
    base_url="https://openrouter.ai/api/v1"
)


# ========== 3. تعریف State ==========
class GraphState(TypedDict):
    question: str
    documents: List[Document]
    answer: str
    session_id: str


# ========== 4. گره بازیابی اسناد ==========
def retrieve(state: GraphState) -> dict:
    """بازیابی اسناد مرتبط از ChromaDB"""
    print(f"🔍 در حال جستجو: {state['question']}")

    vectorstore = Chroma(
        persist_directory=str(CHROMA_PATH),
        embedding_function=embeddings
    )

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 4}  # تعداد اسناد برگشتی
    )

    docs = retriever.invoke(state["question"])
    print(f"📚 تعداد اسناد پیدا شده: {len(docs)}")

    return {"documents": docs}


# ========== 5. گره تولید پاسخ ==========
def generate(state: GraphState) -> dict:
    """تولید پاسخ بر اساس اسناد بازیابی شده"""

    if not state["documents"]:
        return {"answer": "اطلاعاتی پیدا نشد. لطفاً سوال خود را دقیق‌تر بپرسید."}

    # ساخت زمینه از اسناد
    context_parts = []
    for i, doc in enumerate(state["documents"][:4], 1):
        content = doc.page_content[:600]
        source = doc.metadata.get("source", "نامشخص")
        context_parts.append(f"متن {i} (منبع: {source}):\n{content}")

    context = "\n\n---\n\n".join(context_parts)

    # گرفتن تاریخچه جلسه جاری
    session_id = state.get("session_id", "default")
    recent_history = history.get_by_session(session_id, limit=3)

    history_text = ""
    if recent_history:
        history_text = "\n\n## تاریخچه مکالمات قبلی:\n"
        for h in recent_history[:3]:
            history_text += f"- سوال: {h['question']}\n- پاسخ: {h['answer'][:150]}...\n\n"

    # ساخت پرامپت نهایی
    prompt = f"""شما یک دستیار هوشمند برای دانشگاه پیام نور هستید.
بر اساس اطلاعات زیر به سوال کاربر پاسخ دهید.

{history_text}

## اطلاعات موجود:
{context}

## سوال کاربر:
{state['question']}

## قوانین:
1. فقط بر اساس اطلاعات بالا پاسخ دهید
2. اگر پاسخ در اطلاعات نیست، بگویید "اطلاعی ندارم"
3. پاسخ مختصر، مفید و به زبان فارسی روان باشد
4. اگر چند منبع دارید، می‌توانید ترکیب کنید

پاسخ:"""

    try:
        response = llm.invoke(prompt)
        answer = response.content

        # ذخیره در تاریخچه
        history.add(
            question=state["question"],
            answer=answer,
            session_id=session_id,
            source_count=len(state["documents"])
        )

        return {"answer": answer, "documents": state["documents"]}

    except Exception as e:
        error_msg = f"خطا در تولید پاسخ: {str(e)}"
        print(error_msg)
        return {"answer": "خطایی رخ داد. لطفاً دوباره تلاش کنید."}


# ========== 6. ساخت گراف ==========
def create_graph():
    """ساخت گراف LangGraph"""
    workflow = StateGraph(GraphState)

    # اضافه کردن گره‌ها
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)

    # اضافه کردن لبه‌ها
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# ========== 7. نمونه گراف ==========
graph = create_graph()


# ========== 8. تابع کمکی برای استفاده آسان ==========
def ask(question: str, session_id: str = "default") -> str:
    """تابع ساده برای پرسیدن سوال"""
    result = graph.invoke({
        "question": question,
        "session_id": session_id
    })
    return result["answer"]


# ========== 9. اجرای تست ==========
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 تست گراف RAG")
    print("=" * 60)

    test_question = "چطور فارغ التحصیل شوم؟"
    print(f"\n❓ سوال: {test_question}")
    print("\n⏳ در حال پردازش...")

    result = graph.invoke({
        "question": test_question,
        "session_id": "test_user"
    })

    print("\n" + "=" * 60)
    print("📝 پاسخ:")
    print(result["answer"])
    print(f"\n📚 تعداد منابع: {len(result.get('documents', []))}")
    print("=" * 60)