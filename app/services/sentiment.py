import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Use GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
# print("Using device:", device)

# Path to your saved model
MODEL_PATH = "app/sentiment_model"

# Load tokenizer and model once at startup
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()

# Map output indices to labels
LABELS = {0: "negative", 1: "neutral", 2: "positive"}

def analyze_sentiment(text: str):
    if not text.strip():
        return "neutral", 1.0
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = F.softmax(logits, dim=-1)
        pred_class = torch.argmax(probs, dim=-1).item()
    return LABELS[pred_class], probs[0, pred_class].item()

