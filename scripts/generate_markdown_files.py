import os
import time
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY")
JINA_KEY = os.environ.get("JINA_AI_API_KEY")

URLS_TO_TEST = [
    "https://techcrunch.com/2024/05/14/google-io-2024-everything-announced/",
    "https://www.theverge.com/2023/9/12/23867613/apple-iphone-15-pro-max-usb-c-action-button-a17-bionic",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/",
    "https://hypebeast.com/2024/6/givenchy-juergen-teller-campaign-sarah-burton-ss27-paris-fashion-week-info"
]

OUTPUT_DIR = "scraper_tests"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def slugify(url):
    domain = urlparse(url).netloc.replace('www.', '')
    path = urlparse(url).path.strip('/').split('/')[-1]
    if not path:
        path = "home"
    slug = f"{domain}_{path}"
    # clean invalid chars
    return "".join(c for c in slug if c.isalnum() or c in ('_', '-'))

def test_firecrawl(url, slug):
    print(f"[Firecrawl] Fetching {url}...")
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "waitFor": 3000
    }
    try:
        response = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        md = response.json().get("data", {}).get("markdown", "")
        
        filepath = os.path.join(OUTPUT_DIR, f"{slug}_firecrawl.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)
    except Exception as e:
        print(f"Firecrawl error on {url}: {e}")

def test_jina(url, slug):
    print(f"[Jina AI] Fetching {url}...")
    headers = {
        "Authorization": f"Bearer {JINA_KEY}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=60)
        if response.status_code == 202:
            print(f"Jina AI 202 Accepted on {url} (Timeout)")
            return
            
        response.raise_for_status()
        md = response.json().get("data", {}).get("content", "")
        
        filepath = os.path.join(OUTPUT_DIR, f"{slug}_jina.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)
    except Exception as e:
        print(f"Jina error on {url}: {e}")

def run():
    print(f"Starting markdown extraction test for {len(URLS_TO_TEST)} URLs...\n")
    for url in URLS_TO_TEST:
        slug = slugify(url)
        test_firecrawl(url, slug)
        test_jina(url, slug)
        print("---")
        time.sleep(2)
    print("Done! Check the scraper_tests directory.")

if __name__ == "__main__":
    run()
