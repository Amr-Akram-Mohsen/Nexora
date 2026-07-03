import sys
import os
import json
import requests
from flask import current_app

# Add the parent directory to sys.path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core import create_app

app = create_app()

def test_firecrawl(url: str):
    api_key = app.config.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: FIRECRAWL_API_KEY not found in config.")
        return

    print(f"Testing Firecrawl on {url}...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "formats": ["markdown", "html"],
        "waitFor": 3000,
        "timeout": 30000,
        "onlyMainContent": True
    }

    try:
        response = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        with open("firecrawl_output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Successfully saved firecrawl_output.json")
    except Exception as e:
        print(f"Firecrawl failed: {e}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(e.response.text)

def test_jina_ai(url: str):
    api_key = app.config.get("JINA_AI_API_KEY")
    if not api_key:
        print("Error: JINA_AI_API_KEY not found in config.")
        return

    print(f"\nTesting Jina AI Reader on {url}...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "X-Return-Format": "markdown" 
    }
    
    try:
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        with open("jina_output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Successfully saved jina_output.json")
    except Exception as e:
        print(f"Jina AI failed: {e}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(e.response.text)

if __name__ == "__main__":
    test_url = "https://hypebeast.com/2024/6/givenchy-juergen-teller-campaign-sarah-burton-ss27-paris-fashion-week-info"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        
    with app.app_context():
        test_firecrawl(test_url)
        test_jina_ai(test_url)
