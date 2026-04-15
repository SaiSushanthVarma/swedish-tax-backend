import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

URLS = [
    # Already working
    "https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/enskildnaringsverksamhet.4.5c13cb6b1198121ee8580002518.html",
    "https://www.skatteverket.se/foretag/drivaforetag/startaochregistrera/fordigsomvillstartaforetag.4.6e8a1495181dad540842251.html",
    # New
    "https://www.skatteverket.se/foretag/drivaforetag/startaochregistrera.4.58d555751259e4d661680006123.html",
    "https://www.skatteverket.se/foretag/inkomstdeklaration/deklareraenskildnaringsverksamhet.4.133ff59513d6f9ee2ebf00.html",
    "https://www.skatteverket.se/privat/skatter/arbeteochinkomst/deklarera.4.html",
    "https://www.skatteverket.se/foretag/drivaforetag/enskildnaringsverksamhet.4.5c13cb6b1198121ee8580002518.html",
    "https://www.skatteverket.se/privat/etjansterochblanketter/blanketterbroschyrer/broschyrer/info/425.4.39f16f103821c58f680007809.html",
    "https://www.skatteverket.se/foretag/etjansterochblanketter/blanketterbroschyrer/broschyrer/info/403.4.39f16f103821c58f680007749.html",
    # Reseavdrag (replaces SKV 500)
    "https://www.skatteverket.se/privat/skatter/arbeteochinkomst/avdrag/resortillochfranarbetet.4.html",
    # Förmåner (replaces SKV 341)
    "https://www.skatteverket.se/privat/skatter/arbeteochinkomst/formaner.4.html",
    # Avdrag lexikon — huge resource
    "https://www.skatteverket.se/privat/skatter/arbeteochinkomst/avdrag.4.html",
    # ROT och RUT
    "https://www.skatteverket.se/privat/fastigheterochbostad/rotochrutarbete.4.html",
    # Starta företag
    "https://www.skatteverket.se/foretag/drivaforetag/startaochregistrera.4.html",
    # Moms grundläggande
    "https://www.skatteverket.se/foretag/moms.4.html",
    # Pension och skatt
    "https://www.skatteverket.se/privat/pension.4.html",
]

OUTPUT_DIR = Path("../docs/web")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research bot)"}


def url_to_filename(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = path.replace("/", "_")
    return f"{slug}.txt"


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 50]
    return "\n".join(lines)


def scrape():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for url in URLS:
        try:
            filename = url_to_filename(url)
            dest = OUTPUT_DIR / filename

            if dest.exists():
                print(f"  Already exists: {filename}")
                continue

            print(f"Scraping: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30)

            if response.status_code != 200:
                print(f"  ⚠ HTTP {response.status_code} — skipping")
                continue

            text = extract_text(response.text)

            if not text.strip():
                print(f"  ⚠ No content extracted — skipping")
                continue

            dest.write_text(text, encoding="utf-8")
            print(f"  ✓ Saved {len(text)} chars → {filename}")

        except Exception as e:
            print(f"  ⚠ Failed to scrape {url}: {e}, skipping")

        time.sleep(2)

    print("\nDone.")


if __name__ == "__main__":
    scrape()
