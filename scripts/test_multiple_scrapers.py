import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY")
JINA_KEY = os.environ.get("JINA_AI_API_KEY")

URLS_TO_TEST = [
    # A heavy JS news site
    "https://techcrunch.com/2024/05/14/google-io-2024-everything-announced/",
    # A blog/developer site
    "https://github.blog/2024-05-13-github-copilot-azure/",
    # A standard e-commerce/product page or simpler article
    "https://www.wired.com/story/apple-ipad-pro-m4-review/"
]

def test_firecrawl(url):
    print(f"\n[Firecrawl] Fetching {url}...")
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "pageOptions": {
            "onlyMainContent": True,
            "waitFor": 3000
        }
    }
    
    try:
        response = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload, timeout=35)
        response.raise_for_status()
        data = response.json().get("data", {})
        
        md_len = len(data.get("markdown", ""))
        html_len = len(data.get("html", ""))
        return {"status": "success", "markdown_length": md_len, "html_length": html_len}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def test_jina(url):
    print(f"[Jina AI] Fetching {url}...")
    headers = {
        "Authorization": f"Bearer {JINA_KEY}",
        "Accept": "application/json"
    }
    try:
        # Increase timeout and maybe don't use application/json if we just want markdown, but we want metadata too
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=35)
        if response.status_code == 202:
            return {"status": "timeout (202)", "markdown_length": 0, "html_length": 0}
            
        response.raise_for_status()
        data = response.json().get("data", {})
        
        md_len = len(data.get("content", ""))
        # Jina returns markdown natively, HTML is not provided in standard json response unless requested specifically
        return {"status": "success", "markdown_length": md_len, "html_length": 0}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def run_tests():
    results = {}
    for url in URLS_TO_TEST:
        results[url] = {
            "firecrawl": test_firecrawl(url),
            "jina": test_jina(url)
        }
        time.sleep(2) # rate limit prevention
        
    # Write report
    with open("multi_scraper_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n--- Test Complete. Wrote multi_scraper_report.json ---")

if __name__ == "__main__":
    run_tests()
