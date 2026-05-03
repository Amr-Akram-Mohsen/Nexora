import logging
import difflib
from urllib.parse import urlparse
from app.integrations.content.article_utils.extract_article_content import scrape_article_content
from app.integrations.content.article_utils.extractor_clients import extract_with_apis
from app.integrations.content.article_utils.quality import score_content_quality
from app.integrations.content.article_utils.content_normalizer import normalize_content, text_to_html

logger = logging.getLogger(__name__)

# ── Trusted sources (eligible for full-content scraping) ───────
TRUSTED_DOMAINS = {
    "theverge.com", "wired.com", "engadget.com", "techcrunch.com",
    "gsmarena.com", "macrumors.com", "9to5mac.com", "androidcentral.com",
    "tomsguide.com", "digitaltrends.com", "cnet.com", "zdnet.com",
    "arstechnica.com", "venturebeat.com", "gizmodo.com", "slashgear.com",
    "pocket-lint.com", "trustedreviews.com", "whathifi.com", "stuff.tv",
    "pcgamer.com", "eurogamer.net", "ign.com", "gamespot.com", "polygon.com",
}

def is_trusted(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        return domain in TRUSTED_DOMAINS or any(domain.endswith("." + d) for d in TRUSTED_DOMAINS)
    except Exception:
        return False

def _is_similar(text1: str, text2: str) -> bool:
    if not text1 or not text2:
        return False
    # Quick length check first
    len1, len2 = len(text1), len(text2)
    if abs(len1 - len2) > max(len1, len2) * 0.2:
        return False
    # Use the first 1000 chars for fast similarity check
    ratio = difflib.SequenceMatcher(None, text1[:1000], text2[:1000]).ratio()
    return ratio > 0.85

from app.shared.dto.ingestion import ClassifiedItemDTO, EnrichedItemDTO

def route_enrichment_strategy(item: ClassifiedItemDTO) -> EnrichedItemDTO:
    """
    Routes enrichment based on content source/type.
    Avoids scraping social media domains directly.
    """
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    url = data.get("url", "").lower()
    
    if "youtube.com" in url or "reddit.com" in url:
        return EnrichedItemDTO(**data)
        
    return enrich_article_content(item)

def enrich_article_content(item: ClassifiedItemDTO) -> EnrichedItemDTO:
    """
    Core content strategy layer.
    Evaluates API, Extractor, Scraper, and Fallback.
    Selects the best candidate based on quality scoring non-sequentially.
    """
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    url = data.get("url", "")
    description = data.get("description", "")
    
    candidates = []
    trusted = is_trusted(url)
    is_youtube = "youtube.com" in url.lower()
    
    # --- 1. Candidate: Existing API full content ---
    initial_content = data.get("content", "")
    if initial_content:
        norm = normalize_content(initial_content, None)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append({
            "content_html": norm["content_html"],
            "content_text": norm["content_text"],
            "word_count": norm["word_count"],
            "quality_score": score,
            "is_content_scraped": False,
            "content_source": "api"
        })
    
    best_existing_wc = candidates[0]["word_count"] if candidates else 0
    extractor_failed = False
    
    # --- 2. Candidate: Extractor APIs ---
    if not is_youtube and (not initial_content or best_existing_wc < 200):
        if trusted or not initial_content:
            logger.info(f"[Enrichment] Trying extractor APIs for domain: {url}")
            extractor_result = extract_with_apis(url)
            if extractor_result:
                # extractor_clients.py provides "diffbot" or "mercury" as source
                candidates.append({
                    "content_html": extractor_result["content_html"],
                    "content_text": extractor_result["content_text"],
                    "word_count": extractor_result["word_count"],
                    "quality_score": extractor_result["quality_score"],
                    "is_content_scraped": False,  # API extraction is not considered "scraped"
                    "content_source": extractor_result["source"]
                })
            else:
                extractor_failed = True

    # --- 3. Candidate: Scraper Fallback ---
    # Strict gating: (missing or short) AND (trusted or extractor failed)
    best_wc_so_far = max([c["word_count"] for c in candidates]) if candidates else 0
    
    if not is_youtube and (not initial_content or best_wc_so_far < 200):
        if trusted or extractor_failed:
            logger.info(f"[Enrichment] Scraper triggered for: {url}")
            # Note: The scraper logic handles its own timeout/fallbacks internally
            scraped_html = scrape_article_content(url)
            if scraped_html:
                norm = normalize_content(scraped_html, None)
                score = score_content_quality(norm["content_html"], norm["content_text"])
                candidates.append({
                    "content_html": norm["content_html"],
                    "content_text": norm["content_text"],
                    "word_count": norm["word_count"],
                    "quality_score": score,
                    "is_content_scraped": True,
                    "content_source": "scraper"
                })

    # --- 4. Candidate: Description Fallback ---
    if description:
        norm = normalize_content(text_to_html(description), description)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append({
            "content_html": norm["content_html"],
            "content_text": norm["content_text"],
            "word_count": norm["word_count"],
            "quality_score": score,
            "is_content_scraped": False,
            "content_source": "fallback"
        })
        
    # --- Deduplicate Candidates ---
    unique_candidates = []
    for c in candidates:
        is_duplicate = False
        for uc in unique_candidates:
            if _is_similar(c["content_text"], uc["content_text"]):
                # Keep the one with the higher quality score
                if c["quality_score"] > uc["quality_score"]:
                    unique_candidates.remove(uc)
                else:
                    is_duplicate = True
                break
        if not is_duplicate:
            unique_candidates.append(c)

    candidates = unique_candidates
        
    # --- Select the BEST candidate ---
    if candidates:
        logger.info("[Enrichment] Candidates evaluated:")
        for c in candidates:
            logger.info(f"  - {c['content_source']}: score={c['quality_score']:.3f} (words: {c['word_count']})")
            
        best_candidate = max(candidates, key=lambda c: c["quality_score"])
        logger.info(f"[Enrichment] Selected source={best_candidate['content_source']} score={best_candidate['quality_score']:.3f}")
    else:
        # Extreme fallback
        logger.warning(f"[Enrichment] No candidates available for: {url}")
        best_candidate = {
            "content_html": "",
            "content_text": "",
            "word_count": 0,
            "quality_score": 0.0,
            "is_content_scraped": False,
            "content_source": "fallback"
        }

    # Merge best candidate back into data
    data.update(best_candidate)
    
    # For backwards compatibility and migration
    data["content"] = best_candidate["content_html"]

    return EnrichedItemDTO(**data)
