from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from rag import ask_question

OLLAMA_BASE_URL = "http://localhost:11434"
CHROMA_PATH = "../chroma_db"
EMBED_MODEL = "mxbai-embed-large"
MODEL_NAME = "qwen3.5:27b"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 RAG API running — model: {MODEL_NAME}")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty.")
    result = ask_question(request.question)
    return {"answer": result["answer"], "sources": result["sources"]}


@app.get("/admin/stats")
def stats():
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    collection = vectorstore._collection
    data = collection.get(include=["metadatas"])
    total_chunks = len(data["ids"])
    filenames = sorted({
        m.get("filename") or m.get("source", "unknown")
        for m in data["metadatas"]
        if m
    })
    return {"total_chunks": total_chunks, "filenames": filenames}
