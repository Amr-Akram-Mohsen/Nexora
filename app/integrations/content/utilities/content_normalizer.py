import re

def strip_html(html_str: str) -> str:
    if not html_str:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_str)
    return " ".join(text.split())

def text_to_html(text: str) -> str:
    if not text:
        return ""
    parts = text.split("\n\n")
    return "".join(f"<p>{p.strip()}</p>" for p in parts if p.strip())

def normalize_content(html: str | None, text: str | None) -> dict:
    """
    Ensures both HTML and text formats are present and computes word count.
    """
    content_html = html or ""
    content_text = text or ""
    
    # Generate missing formats
    if content_html and not content_text:
        content_text = strip_html(content_html)
    elif content_text and not content_html:
        content_html = text_to_html(content_text)
        
    word_count = len(content_text.split()) if content_text else 0
    
    return {
        "content_html": content_html,
        "content_text": content_text,
        "word_count": word_count
    }
