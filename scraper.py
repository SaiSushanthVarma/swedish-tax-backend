import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

URLS = [
    # Already working
    "https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/enskildnaringsverksamhet.4.5c13cb6b1198121ee8580002518.html",
    "https://www.skatteverket.se/foretag/drivaforetag/startaochregistrera/fordigsomvillstartaforetag.4.6e8a1495181dad540842251.html",
    # Reseavdrag — car travel deductions
    "https://www.skatteverket.se/privat/skatter/bilochtrafik/avdragforresortillochfranarbetet.4.3810a01c150939e893f25603.html",
    # Reseavdrag — car specifically
    "https://www.skatteverket.se/privat/skatter/bilochtrafik/avdragforresortillochfranarbetet/resormedbilmotorcykelellermopedbil.4.5c281c7015abecc2e203f23d.html",
    # Reseavdrag — public transport
    "https://www.skatteverket.se/privat/skatter/bilochtrafik/avdragforresortillochfranarbetet/resormedkollektivtrafik.4.515a6be615c637b9aa4122.html",
    # Reseavdrag — calculate your deduction
    "https://www.skatteverket.se/privat/skatter/bilochtrafik/avdragforresortillochfranarbetet/beraknadittreseavdrag.4.515a6be615c637b9aa420e.html",
    # ROT and RUT
    "https://www.skatteverket.se/privat/fastigheterochbostad/rotochrutarbete.4.2e56d4ba1202f95012080002812.html",
    # Förmåner (employee benefits)
    "https://www.skatteverket.se/privat/skatter/arbeteochinkomst/formaner.4.233f91f71260075abe8800020817.html",
    # Deklarera privatperson
    "https://www.skatteverket.se/privat/deklaration.4.html",
    # Moms grundläggande
    "https://www.skatteverket.se/foretag/moms.4.18e1b10334ebe8bc80002417.html",
    # Starta företag
    "https://www.skatteverket.se/foretag/drivaforetag/startaochregistrera.4.58d555751259e4d661680006123.html",
    # Pension och skatt
    "https://www.skatteverket.se/privat/pension/skattpadinpension.4.22501d9e166a8e8d86800015.html",
    # Avdrag lexikon
    "https://www.skatteverket.se/privat/skatter/arbeteochinkomst/avdrag.4.7be5268414bea064694c6ba.html",
    # F-skatt
    "https://www.skatteverket.se/foretag/drivaforetag/enskildnaringsverksamhet/skatterochavgifter/fskattaochfa-skatt.4.361dc8c15312eff6fd2d5f.html",
    # Räntefördelning
    "https://www.skatteverket.se/foretag/drivaforetag/enskildnaringsverksamhet/deklarera/rantedistribution.4.html",
    # Arbetsgivaravgifter
    "https://www.skatteverket.se/foretag/arbetsgivare/arbetsgivaravgifterochskatteavdrag.4.233f91f71260075abe8800022449.html",
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
