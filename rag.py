import os
import re

import requests
from dotenv import load_dotenv
from groq import Groq
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv()

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "qwen3.5:27b"
EMBED_MODEL = "mxbai-embed-large"
CHROMA_PATH = "../chroma_db"

RAG_PROMPT_TEMPLATE = """You are a helpful Swedish tax assistant.
Answer the question based on the context below.
Be helpful and informative. Answer in the same language as the question.
Use the provided document excerpts as your primary source.
Also use your general knowledge about Swedish tax to supplement the answer if needed.

Context:
{context}

Question: {question}

Answer:"""

FALLBACK_PROMPT_TEMPLATE = """You are a helpful Swedish tax assistant.
Answer this question about Swedish tax from your knowledge.
Be helpful, accurate and answer in the same language as the question.

Question: {question}

Answer:"""


def get_vectorstore() -> QdrantVectorStore:
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    return QdrantVectorStore(
        client=client,
        collection_name="swedish_tax",
        embedding=embeddings,
    )


def clean_docs(docs):
    cleaned = []
    for doc in docs:
        text = doc.page_content.strip()
        if len(text) < 150:
            continue
        letter_ratio = sum(c.isalpha() for c in text) / len(text)
        if letter_ratio < 0.50:
            continue
        words = text.split()
        if len(words) < 10:
            continue
        cleaned.append(doc)
    return cleaned


def call_qwen(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen3.5:27b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024,
                "num_ctx": 4096,
            },
            "think": False,
        },
        timeout=300,
    )
    data = response.json()
    answer = data.get("response", "")
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
    return answer.strip()


def call_groq(prompt: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3-32b"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def call_llm(prompt: str) -> str:
    if os.getenv("USE_GROQ") == "true":
        return call_groq(prompt)
    return call_llm(prompt)


def has_good_chunks(docs) -> bool:
    """True if at least 3 docs pass the letter_ratio quality bar."""
    if len(docs) < 3:
        return False
    good = sum(
        1 for doc in docs
        if sum(c.isalpha() for c in doc.page_content) / len(doc.page_content) > 0.5
    )
    return good >= 3


def ask_question(question: str) -> dict:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20,
            "lambda_mult": 0.7,
        },
    )
    docs = clean_docs(retriever.invoke(question))

    if has_good_chunks(docs):
        print(f"RAG path — {len(docs)} good chunks found")
        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        print("Context length:", len(context))
        print("Prompt being sent:", prompt[:500])

        answer = call_llm(prompt)
        print("Cleaned answer:", repr(answer[:200]))

        if not answer:
            answer = "Kunde inte generera svar. Försök igen."

        sources = []
        for doc in docs:
            meta = doc.metadata
            sources.append({
                "page": meta.get("page", 0),
                "snippet": doc.page_content[:200],
                "filename": meta.get("source", ""),
            })

        return {"answer": answer, "sources": sources}

    else:
        print(f"Fallback path — only {len(docs)} usable chunks, answering from model knowledge")
        prompt = FALLBACK_PROMPT_TEMPLATE.format(question=question)

        answer = call_llm(prompt)
        print("Fallback answer:", repr(answer[:200]))

        if not answer:
            answer = "Kunde inte generera svar. Försök igen."

        answer += "\n\n*(Svar baserat på allmän kunskap, ej från dina dokument)*"

        return {"answer": answer, "sources": []}


if __name__ == "__main__":
    result = ask_question("Vad är F-skatt?")
    print("Svar:", result["answer"])
    print("\nKällor:")
    for s in result["sources"]:
        print(f"  - {s['filename']} (sida {s['page']}): {s['snippet'][:100]}...")
