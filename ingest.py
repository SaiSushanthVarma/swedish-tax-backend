import requests
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "qwen3.5:27b"
EMBED_MODEL = "mxbai-embed-large"
CHROMA_PATH = "../chroma_db"
DOCS_PATH = "../docs"
WEB_DOCS_PATH = "../docs/web"

DOWNLOAD_URLS = [
    {
        "url": "https://www.skatteverket.se/download/18.262c54c219391f2e963479c/1740996584047/skatteutrakningsbroschyren-skv425-utgava31.pdf",
        "filename": "skv425-skatteutrakning-2024.pdf",
    },
    {
        "url": "https://www.skatteverket.se/download/18.7da1d2e118be03f8e4f36f2/1708607303747/traktamenten-och-andra-kostnadsersattningar-skv354-utgava-34.pdf",
        "filename": "skv354-traktamenten.pdf",
    },
    {
        "url": "https://www.skatteverket.se/download/18.262c54c219391f2e9632607/1733849404498/teknisk-beskrivning-SKV433-2025-utgava-35.pdf",
        "filename": "skv433-teknisk-beskrivning-2025.pdf",
    },
    {
        "url": "https://www.skatteverket.se/download/18.515a6be615c637b9aa4d3ab/1733305165017/skattetabell-manadslon-2026-skv403-utgava47.pdf",
        "filename": "skv403-skattetabell-2026.pdf",
    },
    {
        "url": "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac98f1/1705998878221/bokforing-bokslut-deklaration-del1-skv282.pdf",
        "filename": "skv282-bokforing-bokslut.pdf",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_docs():
    docs_dir = Path(DOCS_PATH)
    docs_dir.mkdir(parents=True, exist_ok=True)

    downloaded_count = 0

    for item in DOWNLOAD_URLS:
        dest = docs_dir / item["filename"]
        if dest.exists():
            print(f"Already exists: {item['filename']}")
            continue

        print(f"Downloading: {item['filename']}...")
        try:
            response = requests.get(item["url"], headers=HEADERS, stream=True, timeout=30)
            if response.status_code != 200:
                print(f"  ⚠ Warning: got HTTP {response.status_code} for {item['filename']}, skipping.")
                continue

            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✓ Saved: {item['filename']}")
            downloaded_count += 1

        except requests.RequestException as e:
            print(f"  ⚠ Warning: failed to download {item['filename']}: {e}, skipping.")

    print(f"\n{downloaded_count} file(s) downloaded successfully.")


def is_readable_page(text: str) -> bool:
    if len(text.strip()) < 100:
        return False
    letter_ratio = sum(c.isalpha() for c in text) / len(text)
    return letter_ratio >= 0.45


def ingest():
    docs_dir = Path(DOCS_PATH)
    pdf_files = sorted(docs_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {DOCS_PATH}")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

    total_chunks = 0

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()

        for doc in pages:
            doc.metadata["filename"] = pdf_path.name
            doc.metadata["source"] = str(pdf_path)
            # "page" is already set by PyPDFLoader

        pages = [p for p in pages if is_readable_page(p.page_content)]
        chunks = splitter.split_documents(pages)
        vectorstore.add_documents(chunks)
        total_chunks += len(chunks)
        print(f"✓ Added {len(chunks)} chunks from {pdf_path.name}")

    # Load scraped web .txt files from ../docs/web/
    web_dir = Path(WEB_DOCS_PATH)
    txt_files = sorted(web_dir.glob("*.txt")) if web_dir.exists() else []

    for txt_path in txt_files:
        print(f"Processing: {txt_path.name}")
        loader = TextLoader(str(txt_path), encoding="utf-8")
        docs = loader.load()

        for doc in docs:
            doc.metadata["filename"] = txt_path.name
            doc.metadata["source"] = str(txt_path)

        docs = [d for d in docs if is_readable_page(d.page_content)]
        chunks = splitter.split_documents(docs)
        vectorstore.add_documents(chunks)
        total_chunks += len(chunks)
        print(f"✓ Added {len(chunks)} chunks from {txt_path.name}")

    print(f"\nDone. Total chunks in DB: {total_chunks}")


if __name__ == "__main__":
    download_docs()
    ingest()
