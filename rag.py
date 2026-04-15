import os
import re

import requests
from dotenv import load_dotenv
from groq import Groq
from qdrant_client import QdrantClient

load_dotenv()

MODEL_NAME = "qwen3.5:27b"

HF_EMBED_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "mixedbread-ai/mxbai-embed-large-v1/pipeline/feature-extraction"
)

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


# ── Embeddings ────────────────────────────────────────────────────────────────

def get_embeddings_hf(texts: list) -> list:
    headers = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}
    response = requests.post(HF_EMBED_URL, headers=headers, json={"inputs": texts})
    response.raise_for_status()
    return response.json()


def get_single_embedding(text: str) -> list:
    return get_embeddings_hf([text])[0]


# ── Retrieval ─────────────────────────────────────────────────────────────────

def search_qdrant(question: str, limit: int = 5) -> list[dict]:
    """Return a list of payload dicts from the top matching Qdrant points."""
    embedding = get_single_embedding(question)

    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    results = client.query_points(
        collection_name="swedish_tax",
        query=embedding,
        limit=limit,
    ).points

    return [r.payload for r in results]


def clean_payloads(payloads: list[dict]) -> list[dict]:
    """Filter out short / formula-heavy chunks."""
    cleaned = []
    for p in payloads:
        # Migration stored text under "document"; ingest may use "page_content"
        text = (p.get("document") or p.get("page_content") or "").strip()
        if len(text) < 150:
            continue
        if not text:
            continue
        letter_ratio = sum(c.isalpha() for c in text) / len(text)
        if letter_ratio < 0.50:
            continue
        if len(text.split()) < 10:
            continue
        cleaned.append(p)
    return cleaned


def has_good_chunks(payloads: list[dict]) -> bool:
    """True if at least 3 payloads pass the letter_ratio quality bar."""
    if len(payloads) < 3:
        return False
    good = sum(
        1 for p in payloads
        if (text := (p.get("document") or p.get("page_content") or ""))
        and sum(c.isalpha() for c in text) / len(text) > 0.5
    )
    return good >= 3


# ── LLM ──────────────────────────────────────────────────────────────────────

def call_qwen(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1024, "num_ctx": 4096},
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
    return call_qwen(prompt)


# ── Main entry point ──────────────────────────────────────────────────────────

def ask_question(question: str) -> dict:
    payloads = clean_payloads(search_qdrant(question, limit=5))

    if has_good_chunks(payloads):
        print(f"RAG path — {len(payloads)} good chunks found")
        context = "\n\n".join(
            p.get("document") or p.get("page_content") or "" for p in payloads
        )
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        print("Context length:", len(context))
        print("Prompt being sent:", prompt[:500])

        answer = call_llm(prompt)
        print("Cleaned answer:", repr(answer[:200]))

        if not answer:
            answer = "Kunde inte generera svar. Försök igen."

        sources = []
        for p in payloads:
            text = p.get("document") or p.get("page_content") or ""
            sources.append({
                "page": p.get("page", 0),
                "snippet": text[:200],
                "filename": p.get("source") or p.get("filename") or "",
            })

        return {"answer": answer, "sources": sources}

    else:
        print(f"Fallback path — only {len(payloads)} usable chunks, answering from model knowledge")
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
