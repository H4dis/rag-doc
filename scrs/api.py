from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sys
from pathlib import Path

# اضافه کردن مسیر src به sys.path
sys.path.append(str(Path(__file__).parent))

from graph import graph
from history import history

app = FastAPI(title="RAG API - دانشگاه پیام نور")

# CORS برای اتصال از UI
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


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """پرسیدن سوال - endpoint اصلی"""
    try:
        result = graph.invoke({
            "question": request.question,
            "session_id": request.session_id
        })

        # ذخیره در تاریخچه
        history.add(
            question=request.question,
            answer=result["answer"],
            session_id=request.session_id,
            source_count=len(result.get("documents", []))
        )

        return AskResponse(
            answer=result["answer"],
            question=request.question,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            source_count=len(result.get("documents", []))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{session_id}")
async def get_history(session_id: str, limit: int = 20):
    """گرفتن تاریخچه کاربر"""
    conversations = history.get_by_session(session_id, limit=limit)
    return {"conversations": conversations, "count": len(conversations)}


@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """پاک کردن تاریخچه کاربر"""
    history.clear_session(session_id)
    return {"message": f"تاریخچه {session_id} پاک شد"}


@app.get("/stats")
async def get_stats():
    """آمار کلی"""
    return history.get_stats()

# اجرا: uvicorn src.api:app --reload --port 8000