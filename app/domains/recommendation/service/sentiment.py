import os
import logging
import requests
from flask import current_app
logger = logging.getLogger(__name__)
def analyze_sentiment(text: str):
    HF_API_URL = current_app.config.get('HF_API_URL')
    HF_TOKEN = current_app.config.get('HF_TOKEN')
    if not HF_API_URL:
        return ('neutral', 0)
    if not text.strip():
        return ('neutral', 0)
    headers = {}
    if HF_TOKEN:
        headers['Authorization'] = f'Bearer {HF_TOKEN}'
    try:
        response = requests.post(HF_API_URL, json={'text': text}, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return (data.get('sentiment', 'neutral'), data.get('confidence', 0.5))
    except requests.exceptions.RequestException as e:
        error_msg = f'Sentiment API request failed: {e}'
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f'\nStatus Code: {e.response.status_code}\nResponse: {e.response.text[:200]}'
        logger.warning(error_msg)
        return ('neutral', 0)
    except Exception as e:
        logger.warning('Sentiment API unexpected error: %s', e)
        return ('neutral', 0)