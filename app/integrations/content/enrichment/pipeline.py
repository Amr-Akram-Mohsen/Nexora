import logging
import difflib
from urllib.parse import urlparse
from app.domains.content.service.normalization import (
    normalize_content_shaping as normalize_content,
    text_to_html,
)

def score_content_quality(content_html: str, content_text: str) -> float:
    if not content_text:
        return 0.0
    words = len(content_text.split())
    if words > 500:
        return 1.0
    elif words > 200:
        return 0.8
    elif words > 50:
        return 0.5
    return 0.2
from app.shared.utils.logging import (
    log_integration_start,
    log_integration_success,
    log_scrape_start,
    log_scrape_success,
    log_scrape_error,
)
from app.shared.dto.ingestion import ClassifiedItemDTO, EnrichedItemDTO
from typing import Any

logger = logging.getLogger(__name__)


_NAME = "enrichment"

# ── Trusted sources (eligible for full-content scraping) ───────────────────────
TRUSTED_DOMAINS_FALLBACK = {
    "theverge.com",
    "bloomberg.com",
    "wsj.com",
    "nytimes.com",
    "wired.com",
    "techcrunch.com",
}


def is_trusted(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        from app.domains.taxonomy.models import Source
        from app.core.extensions import db
        
        source = db.session.query(Source).filter(Source.domain == domain).first()
        if source and source.authority_score >= 80:
            return True
            
        return domain in TRUSTED_DOMAINS_FALLBACK or any(
            domain.endswith("." + d) for d in TRUSTED_DOMAINS_FALLBACK
        )
    except Exception:
        return False

def is_blacklisted(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        return domain in {
            "guru3d.com",
            "in.investing.com",
            "seekingalpha.com",
            "storyboard18.com",
            "thehansindia.com",
            "klgadgetguy.com",
            "newswav.com"
        }
    except Exception:
        return False


def _is_similar(text1: str, text2: str) -> bool:
    if not text1 or not text2:
        return False
    len1, len2 = len(text1), len(text2)
    if abs(len1 - len2) > max(len1, len2) * 0.2:
        return False
    ratio = difflib.SequenceMatcher(None, text1[:1000], text2[:1000]).ratio()
    return ratio > 0.85


# ── PHASE 1: DISCOVERY ENRICHMENT (Lightweight / All Content Types) ───────────


def normalize_ingested_data(product: Any) -> EnrichedItemDTO:
    """
    Standardizes and sanitizes raw metadata from discovery APIs.
    Used for ALL content types (Articles, Videos, Posts).
    Performs NO network calls.
    """
    data = product.model_dump() if hasattr(product, "model_dump") else dict(product)

    # 1. Basic Sanitization
    content_raw = data.get("content", "") or data.get("description", "")
    if content_raw:
        norm = normalize_content(content_raw, data.get("description", ""))
        data.update(
            {
                "content_html": norm["content_html"],
                "content_text": norm["content_text"],
                "word_count": norm["word_count"],
                "quality_score": score_content_quality(
                    norm["content_html"], norm["content_text"]
                ),
                "content": norm["content_html"],  # Backwards compatibility
            }
        )

    # Ensure mandatory fields exist
    data.setdefault("is_content_scraped", False)
    data.setdefault("ingestion_method", "api")

    return EnrichedItemDTO(**data)


def ingest_enrichment_router(product: ClassifiedItemDTO) -> EnrichedItemDTO:
    """
    Entry point for Phase 1 Ingestion.
    Ensures discovery is lightning fast by only performing local normalization.
    """
    url = (product.url or "").lower()

    # Passthrough for non-article types or specific platforms if needed
    if "youtube.com" in url or "reddit.com" in url:
        return normalize_ingested_data(product)

    return normalize_ingested_data(product)


# ── PHASE 2: HEAVY ENRICHMENT (Scraping / Articles Only) ──────────────────────


def full_article_scraping_pipeline(product: Any, extractor_service: str = "diffbot") -> EnrichedItemDTO:
    """
    Entry point for Phase 2 Background Worker.
    Performs heavy network-based enrichment (Scraping, Extractor APIs).
    Targets only Articles.
    """
    data = product.model_dump() if hasattr(product, "model_dump") else dict(product)
    url = data.get("url", "")
    description = data.get("description", "")

    if not url:
        return normalize_ingested_data(product)

    log_integration_start(logger, _NAME, mode="phase_2_heavy", url=url[:80])

    candidates = []
    trusted = is_trusted(url)
    
    if is_blacklisted(url):
        logger.info("[enrichment] skipping diffbot scrape for blacklisted source: %s", url)
        return normalize_ingested_data(product)

    # 1. Candidate: API/Initial Content (Local)
    initial_content = data.get("content", "")
    if initial_content:
        norm = normalize_content(initial_content, None)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append(
            {
                "content_html": norm["content_html"],
                "content_text": norm["content_text"],
                "word_count": norm["word_count"],
                "quality_score": score,
                "is_content_scraped": False,
                "ingestion_method": "api",
            }
        )

    # Concurrent Fetching using ThreadPoolExecutor
    import concurrent.futures
    from app.application.content.ingestion.scraper_pipeline import fetch_and_clean_diffbot

    def _fetch_extractor():
        try:
            log_scrape_start(logger, url)

            res = fetch_and_clean_diffbot(url, hero_image_url=data.get("image_url"))

            score = score_content_quality(res["content_html"], res["content_text"])

            source_name = res.get("ingestion_method", "diffbot")
            log_scrape_success(logger, url, words=len(res.get("content_text", "").split()), source=source_name)

            metadata = res["metadata"] # Full diffbot JSON object
            
            authors = metadata.get("authors")
            if not authors and metadata.get("author"):
                authors = [{"name": metadata.get("author")}]
                
            image_url = metadata.get("icon") or data.get("image_url") # or primary image
            
            # Diffbot has an images array, grab the primary
            diffbot_images = metadata.get("images", [])
            for img in diffbot_images:
                if img.get("primary"):
                    image_url = img.get("url")
                    break

            # Diffbot often returns the first paragraph as the summary. 
            # Nullify it to prevent redundant "AI Summary" UI blocks.
            summary = metadata.get("summary")
            content_text = res.get("content_text", "")
            if summary:
                clean_summary = summary.strip()
                if content_text and content_text.strip().startswith(clean_summary):
                    summary = None
                elif content_text and clean_summary in content_text[:len(clean_summary) + 150]:
                    summary = None
                elif description and clean_summary == description.strip():
                    summary = None

            return {
                "content_html":     res.get("content_html"),
                "content_text":     content_text,
                "word_count":       len(content_text.split()),
                "quality_score":    score,
                "is_content_scraped": True,
                "ingestion_method": "diffbot",
                "authors":          authors,
                "extended_metadata": metadata, # raw tags/categories preserved here for the inserter
                "images":           res["images"],
                "videos":           metadata.get("videos"),
                "summary":          summary,
                "language":         metadata.get("humanLanguage"),
                "sentiment_score":  metadata.get("sentiment"),
                "external_uri":     metadata.get("diffbotUri"),
                "image_url":        image_url,
            }
        except Exception as e:
            log_scrape_error(logger, url, reason=str(e))
        return None

    res = _fetch_extractor()
    if res:
        candidates.append(res)
    
    # Add a delay to respect API rate limits (Diffbot is 1 request/sec on free tier)
    import time
    time.sleep(1.5)

    # 4. Fallback (Local)
    if not candidates and description:
        norm = normalize_content(text_to_html(description), description)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append(
            {
                "content_html": norm["content_html"],
                "content_text": norm["content_text"],
                "word_count": norm["word_count"],
                "quality_score": score,
                "is_content_scraped": False,
                "ingestion_method": "fallback",
            }
        )

    # 5. Final Selection & Metadata Recovery
    if candidates:
        best_candidate = max(candidates, key=lambda c: c["quality_score"])
    else:
        return normalize_ingested_data(product)

    selected_image = data.get("image_url")
    canonical_url = data.get("canonical_url")

    # Metadata Recovery (HEAD/Lightweight Scrape)
    if not selected_image:
        selected_image = best_candidate.get("image_url")

    # Update state
    data.update(best_candidate)
    data.update(
        {
            "image_url": selected_image,
            "canonical_url": canonical_url,
        }
    )

    log_integration_success(
        logger,
        _NAME,
        products=1,
        source=best_candidate["ingestion_method"],
        score=f"{best_candidate['quality_score']:.3f}",
        words=best_candidate["word_count"],
        mode="phase_2_full",
    )
    return EnrichedItemDTO(**data)
