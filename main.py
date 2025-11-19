import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

from database import create_document, get_documents, db

app = FastAPI(title="Tanim AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client session identifier")
    message: str = Field(..., min_length=1, description="User message content")
    model: Optional[str] = Field(None, description="Optional model name")


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]


@app.get("/")
def read_root():
    return {"message": "Tanim AI Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Tanim AI backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


def generate_reply(user_text: str) -> str:
    """
    Lightweight built-in model stub.
    Creates a helpful, stylized response while we avoid external dependencies.
    """
    if not user_text.strip():
        return "I'm here. Ask me anything about code, ideas, or tech."

    # Simple transformation for some flair
    summary_hint = user_text.strip()
    if len(summary_hint) > 120:
        summary_hint = summary_hint[:117] + "..."

    return (
        "⚡ Tanim AI • Insight\n"
        f"You said: \"{summary_hint}\"\n\n"
        "Here's a thoughtful response: I can help you plan, outline, and implement this. "
        "If you'd like, ask for a step-by-step plan or a quick prototype."
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Ensure database is configured
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Persist user message
    user_doc = {
        "session_id": req.session_id,
        "role": "user",
        "content": req.message,
        "model": req.model or "tanim-stub",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    create_document("message", user_doc)

    # Generate assistant reply
    reply_text = generate_reply(req.message)
    asst_doc = {
        "session_id": req.session_id,
        "role": "assistant",
        "content": reply_text,
        "model": req.model or "tanim-stub",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    create_document("message", asst_doc)

    # Fetch last 50 messages for session
    docs = get_documents("message", {"session_id": req.session_id}, limit=50)
    messages = [
        ChatMessage(role=d.get("role"), content=d.get("content"), created_at=d.get("created_at", datetime.now(timezone.utc)))
        for d in docs
    ]
    return ChatResponse(session_id=req.session_id, messages=messages)


@app.get("/api/history", response_model=ChatResponse)
def history(session_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    docs = get_documents("message", {"session_id": session_id}, limit=50)
    messages = [
        ChatMessage(role=d.get("role"), content=d.get("content"), created_at=d.get("created_at", datetime.now(timezone.utc)))
        for d in docs
    ]
    return ChatResponse(session_id=session_id, messages=messages)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
