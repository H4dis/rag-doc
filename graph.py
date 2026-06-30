from pathlib import Path
from typing import TypedDict, List
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from history import history

os.environ["OPENROUTER_API_KEY"] = "or-کلیدت_اینجا"

CACHE_DIR = Path("C:/Users/ASUS/.cache/huggingface/hub")
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)

CHROMA_PATH = Path("chroma_db")

print("Loading Embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    cache_folder=str(CACHE_DIR),
    encode_kwargs={'normalize_embeddings': True}
)

print("Connecting to OpenRouter...")
llm = ChatOpenRouter(
    model="openrouter/free",
    temperature=0.3,
    max_tokens=500,
    base_url="https://openrouter.ai/api/v1"
)


class GraphState(TypedDict):
    question: str
    documents: List[Document]
    answer: str
    session_id: str


def retrieve(state: GraphState) -> dict:
    print(f"Searching: {state['question']}")
    vectorstore = Chroma(
        persist_directory=str(CHROMA_PATH),
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(state["question"])
    print(f"Found {len(docs)} documents")
    return {"documents": docs}


def generate(state: GraphState) -> dict:
    if not state["documents"]:
        return {"answer": "No information found. Please ask more specifically."}

    context_parts = []
    for i, doc in enumerate(state["documents"][:4], 1):
        content = doc.page_content[:600]
        source = doc.metadata.get("source", "unknown")
        context_parts.append(f"Text {i} (source: {source}):\n{content}")

    context = "\n\n---\n\n".join(context_parts)

    session_id = state.get("session_id", "default")
    recent_history = history.get_by_session(session_id, limit=3)

    history_text = ""
    if recent_history:
        history_text = "\n\nPrevious conversations:\n"
        for h in recent_history[:3]:
            history_text += f"- Q: {h['question']}\n- A: {h['answer'][:150]}...\n\n"

    prompt = f"""You are a smart assistant for Payam Noor University.
Answer the user's question based on the information below.

{history_text}

## Available information:
{context}

## User question:
{state['question']}

## Rules:
1. Only answer based on the information above
2. If the answer is not in the information, say "I don't know"
3. Answer briefly, useful, and in fluent Persian

Answer:"""

    try:
        response = llm.invoke(prompt)
        answer = response.content

        history.add(
            question=state["question"],
            answer=answer,
            session_id=session_id,
            source_count=len(state["documents"])
        )

        return {"answer": answer, "documents": state["documents"]}
    except Exception as e:
        error_msg = f"Error generating answer: {str(e)}"
        print(error_msg)
        return {"answer": "An error occurred. Please try again."}


def create_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()


graph = create_graph()


def ask(question: str, session_id: str = "default") -> str:
    result = graph.invoke({
        "question": question,
        "session_id": session_id
    })
    return result["answer"]


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing RAG Graph")
    print("=" * 60)

    test_question = "How to graduate?"
    print(f"\nQ: {test_question}")
    print("\nProcessing...")

    result = graph.invoke({
        "question": test_question,
        "session_id": "test_user"
    })

    print("\n" + "=" * 60)
    print("Answer:")
    print(result["answer"])
    print(f"\nSources: {len(result.get('documents', []))}")
    print("=" * 60)