"""
Stage 1: Light Markdown Preprocessing
--------------------------------------
Performs the minimal, always-safe cleanup that every piece of markdown
needs before any structural analysis can take place.

Operations (order matters):
  1. Strip image alt text — keeps the image URL, drops the alt string.
  2. Remove Wikipedia-style citation brackets — [1], [[2]](url).
  3. Collapse consecutive blank lines (3+) down to 2.
"""
import re


def run(md: str) -> str:
    md = _strip_image_alt_text(md)
    md = _fix_linked_images(md)
    md = _fix_empty_links_to_images(md)
    md = _remove_empty_links(md)
    md = _remove_wikipedia_citations(md)
    md = _clean_malformed_html(md)
    md = _remove_inline_image_credits(md)
    md = _collapse_blank_lines(md)
    return md


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_image_alt_text(md: str) -> str:
    """Replace `![alt text](url)` with `![](url)` — keeps the image, drops noise."""
    return re.sub(r'!\[.*?\]\((.*?)\)', r'![](\1)', md)

def _fix_linked_images(md: str) -> str:
    """Fix `[![](img_url)](link_url)` -> `![](img_url)`"""
    return re.sub(r'\[\s*!\[.*?\]\((.*?)\)\s*\]\((.*?)\)', r'![](\1)', md)

def _fix_empty_links_to_images(md: str) -> str:
    """Fix `[](https://.../img.jpg)` -> `![](https://.../img.jpg)`"""
    return re.sub(r'(?<!\!)\[\s*\]\(([^)]+\.(?:jpg|jpeg|png|gif|webp|svg)(?:\?[^)]*)?)\)', r'![](\1)', md, flags=re.IGNORECASE)

def _remove_empty_links(md: str) -> str:
    """Remove `[](url)` entirely if it's not an image"""
    return re.sub(r'(?<!\!)\[\s*\]\((.*?)\)', '', md)

def _remove_wikipedia_citations(md: str) -> str:
    """Remove citation markers like [1], [[2]], [[3]](url)."""
    md = re.sub(r'\[\\?\[\d+\\?\]\]\([^\)]+\)', '', md)  # [[1]](url)
    md = re.sub(r'\[\d+\]', '', md)                        # [1]
    return md

def _clean_malformed_html(md: str) -> str:
    """Remove `target=\"<em>blank` or similar artifacts."""
    return re.sub(r'target=".*?blank"?', '', md, flags=re.IGNORECASE)

def _remove_inline_image_credits(md: str) -> str:
    """Remove (Image credit: Future) inside markdown."""
    md = re.sub(r'\*?\*?\(?(?:Image|Photo)\s+(?:credit|by):.*?\)?\*?\*?', '', md, flags=re.IGNORECASE)
    return md

def _collapse_blank_lines(md: str) -> str:
    """Collapse 3 or more consecutive blank lines into exactly 2."""
    return re.sub(r'\n{3,}', '\n\n', md)
