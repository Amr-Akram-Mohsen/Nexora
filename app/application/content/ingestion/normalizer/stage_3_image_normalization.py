r"""
Stage 3: Image Normalization
-----------------------------
Filters out images that are clearly publisher chrome rather than genuine
article content. Returns a set of approved image URLs that the block
parser may include, and removes bad images from the markdown in-place.

Rejection criteria (publisher-agnostic URL heuristics):
  - URL contains chrome path segments: /avatar/, /author/, /logo/, /icon/,
    /ad/, /ads/, /sponsor/, /badge/, /pixel/, /tracking/, /widget/
  - URL matches a pixel-tracking pattern (1x1, pixel.gif, etc.)
  - Dimensions in the URL suggest a thumbnail: -\\d+x\\d+ where both
    dimensions are < 120 (icon-sized thumbnails)
  - URL is identical to the article's hero image_url (already shown in header)
"""
import re
from urllib.parse import urlparse


_CHROME_PATH_SEGMENTS = {
    'avatar', 'author', 'logo', 'icon', 'icons',
    'ad', 'ads', 'advertisement', 'sponsor', 'sponsored',
    'badge', 'pixel', 'tracking', 'tracker', 'widget',
    'blank', 'spacer', 'placeholder',
}

_PIXEL_PATTERNS = [
    r'1x1\.(gif|png|jpg)',
    r'pixel\.(gif|png|jpg)',
    r'tracking\.(gif|png|jpg)',
    r'beacon\.(gif|png|jpg)',
]

_THUMBNAIL_PATTERN = re.compile(r'-(\d+)x(\d+)(?:@\dx)?\.')


def run(md: str, hero_image_url: str | None = None) -> tuple[str, set[str]]:
    """
    Returns:
        (cleaned_markdown, approved_image_urls)

    Image tags for rejected URLs are removed from the markdown.
    Approved URLs are returned as a set for the block parser to use.
    """
    all_images = re.findall(r'!\[\]\(([^\)]+)\)', md)
    approved: set[str] = set()
    rejected: set[str] = set()

    for url in all_images:
        if _should_reject(url, hero_image_url):
            rejected.add(url)
        else:
            approved.add(url)

    # Remove rejected images from the markdown text
    for url in rejected:
        md = md.replace(f'![]({url})', '')

    return md, approved


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _should_reject(url: str, hero_image_url: str | None) -> bool:
    if not url or not url.startswith('http'):
        return True

    # Exact match with hero image — already rendered in header
    if hero_image_url and url.rstrip('/') == hero_image_url.rstrip('/'):
        return True

    lower = url.lower()

    # Chrome path segment check
    try:
        path_parts = set(urlparse(lower).path.strip('/').split('/'))
        if path_parts & _CHROME_PATH_SEGMENTS:
            return True
    except Exception:
        pass

    # Pixel tracking pattern check
    for pattern in _PIXEL_PATTERNS:
        if re.search(pattern, lower):
            return True

    # Tiny thumbnail check (both dims < 120px)
    m = _THUMBNAIL_PATTERN.search(lower)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if w < 120 and h < 120:
            return True

    return False
