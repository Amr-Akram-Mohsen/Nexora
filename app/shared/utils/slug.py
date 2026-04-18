import re
import unicodedata

def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFKD", name).strip().lower()

def generate_slug(name: str) -> str:
    name = normalize_name(name)
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "-", name)
    return name.strip("-")

