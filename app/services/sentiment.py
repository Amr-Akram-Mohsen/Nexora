import requests, os

HF_API_URL = os.getenv("HF_API_URL")

def analyze_sentiment(text: str):
    if not text.strip():
        return "neutral", 1.0

    try:
        response = requests.post(
            HF_API_URL,
            json={"text": text},
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return data.get("sentiment", "neutral"), data.get("confidence", 0.5)

    except Exception as e:
        print("Sentiment API error:", e)  # optional logging

        # fallback (important for stability)
        return "neutral", 0.5
