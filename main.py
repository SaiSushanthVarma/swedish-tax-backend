import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from qdrant_client import QdrantClient

from rag import ask_question

MODEL_NAME = "qwen3.5:27b"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 RAG API running — model: {MODEL_NAME}")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    history: list = []  # list of {"role": "user/assistant", "content": str}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty.")
    result = ask_question(request.question, request.history)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result.get("confidence"),
        "search_used": result.get("search_used", False),
        "hallucination_flagged": result.get("hallucination_flagged", False),
    }


@app.get("/admin/stats")
def stats():
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    result = client.scroll(
        collection_name="swedish_tax",
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )
    points = result[0]
    total_chunks = len(points)
    filenames = sorted({
        (p.payload or {}).get("filename") or (p.payload or {}).get("source", "unknown")
        for p in points
    })
    return {"total_chunks": total_chunks, "filenames": filenames}
