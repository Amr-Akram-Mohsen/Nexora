# app/domains/interaction/service/insights/learning_memory.py
import os
import json

def load_memory_layer():
    MEMORY_FILE_PATH = os.path.join("instance", "content_intelligence_memory.json")
    if not os.path.exists(MEMORY_FILE_PATH):
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
            seed_data = [
                {"entity": "Smartwatches", "platform": "youtube", "intent": "comparison", "outcome": "success", "impact_score": 0.85},
                {"entity": "Laptops", "platform": "blog", "intent": "buying-guide", "outcome": "success", "impact_score": 0.78},
                {"entity": "Perfumes", "platform": "pinterest", "intent": "gift-ideas", "outcome": "failure", "impact_score": 0.32},
                {"entity": "Bags", "platform": "pinterest", "intent": "gift-ideas", "outcome": "success", "impact_score": 0.82},
                {"entity": "Electronics", "platform": "blog", "intent": "buying-guide", "outcome": "failure", "impact_score": 0.28}
            ]
            with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)
            return seed_data
        except Exception:
            return []
    try:
        with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_memory_layer(data):
    MEMORY_FILE_PATH = os.path.join("instance", "content_intelligence_memory.json")
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving memory layer: {e}")
