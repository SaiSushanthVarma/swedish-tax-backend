"""
Migrate all chunks from local ChromaDB → Qdrant Cloud.

Usage:
    python migrate_to_qdrant.py

Requires in .env:
    QDRANT_URL=https://your-cluster.qdrant.io
    QDRANT_API_KEY=your_api_key
"""

import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

CHROMA_PATH = "../chroma_db"
OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "mxbai-embed-large"
VECTOR_SIZE = 1024          # mxbai-embed-large output dimension
COLLECTION_NAME = "swedish_tax"
BATCH_SIZE = 50             # points per upload batch


def get_chroma_documents():
    """Return all documents + embeddings from ChromaDB."""
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    collection = vectorstore._collection

    print("Reading all chunks from ChromaDB...")
    data = collection.get(include=["documents", "metadatas", "embeddings"])

    ids       = data["ids"]
    documents = data["documents"]
    metadatas = data["metadatas"]
    embeddings_list = data["embeddings"]

    print(f"  Found {len(ids)} chunks in ChromaDB.")
    return ids, documents, metadatas, embeddings_list


def create_qdrant_collection(client: QdrantClient):
    """Create the collection, dropping it first if it already exists."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' already exists — recreating it.")
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Collection '{COLLECTION_NAME}' created (dim={VECTOR_SIZE}, cosine).")


def migrate():
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url or not qdrant_api_key:
        raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in .env")

    # ── Read from Chroma ──────────────────────────────────────────────────
    ids, documents, metadatas, embeddings_list = get_chroma_documents()
    total = len(ids)

    if total == 0:
        print("No chunks found in ChromaDB. Run ingest.py first.")
        return

    if embeddings_list is None or len(embeddings_list) == 0:
        print("ERROR: ChromaDB returned no embeddings.")
        print("Tip: embeddings must be present in the collection.")
        return

    # ── Connect to Qdrant ─────────────────────────────────────────────────
    print(f"\nConnecting to Qdrant at {qdrant_url} ...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    create_qdrant_collection(client)

    # ── Upload in batches ─────────────────────────────────────────────────
    print(f"\nUploading {total} chunks in batches of {BATCH_SIZE}...")
    migrated = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)

        points = []
        for i in range(batch_start, batch_end):
            payload = dict(metadatas[i]) if metadatas[i] else {}
            payload["document"] = documents[i]           # store raw text too

            points.append(
                PointStruct(
                    id=migrated + (i - batch_start),     # sequential int id
                    vector=embeddings_list[i],
                    payload=payload,
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        migrated += len(points)

        if migrated % 100 == 0 or migrated == total:
            print(f"  Progress: {migrated}/{total} chunks uploaded")

    print(f"\nDone! {migrated} chunks migrated to Qdrant collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    migrate()
