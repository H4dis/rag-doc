from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from graph import graph
from history import history
from hybrid_retriever import HybridRetriever

app = FastAPI(title="RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = "web_user"


class AskResponse(BaseModel):
    answer: str
    question: str
    session_id: str
    timestamp: str
    source_count: int


hybrid = HybridRetriever()


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    try:
        result = graph.invoke({
            "question": request.question,
            "session_id": request.session_id
        })

        answer = result["answer"]
        source_count = len(result.get("documents", []))

        if source_count == 0:
            print("No results in DB. Trying hybrid...")
            hybrid_answer = hybrid.ask(request.question)
            if "No information found" not in hybrid_answer:
                answer = hybrid_answer
                source_count = 1

        history.add(
            question=request.question,
            answer=answer,
            session_id=request.session_id,
            source_count=source_count
        )

        return AskResponse(
            answer=answer,
            question=request.question,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            source_count=source_count
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{session_id}")
async def get_history(session_id: str, limit: int = 20):
    conversations = history.get_by_session(session_id, limit=limit)
    return {"conversations": conversations, "count": len(conversations)}


@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    history.clear_session(session_id)
    return {"message": f"History cleared for {session_id}"}


@app.get("/stats")
async def get_stats():
    return history.get_stats()