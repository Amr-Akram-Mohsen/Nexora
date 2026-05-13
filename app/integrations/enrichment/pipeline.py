import logging
import difflib
from urllib.parse import urlparse
from app.integrations.content.article_utils.extract_article_content import scrape_article_content
from app.integrations.content.article_utils.extractor_clients import extract_with_apis
from app.integrations.content.article_utils.quality import score_content_quality
from app.domains.content.service.normalization import (
    sanitize_html as clean_html,
    normalize_content_shaping as normalize_content,
    text_to_html,
    parse_date as normalize_date 
)
from app.integrations.content.article_utils.metadata import recover_article_metadata
from app.shared.utils.logging import (
    log_integration_start, log_integration_success, log_integration_error,
    log_integration_warning, log_scrape_start, log_scrape_success, log_scrape_error,
)

logger = logging.getLogger(__name__)

from typing import Any

_NAME = "enrichment"

# ── Trusted sources (eligible for full-content scraping) ───────────────────────
TRUSTED_DOMAINS = {
    # Technology & Gadgets
    "theverge.com", "wired.com", "engadget.com", "techcrunch.com",
    "gsmarena.com", "macrumors.com", "9to5mac.com", "androidcentral.com",
    "tomsguide.com", "digitaltrends.com", "cnet.com", "zdnet.com",
    "arstechnica.com", "venturebeat.com", "gizmodo.com", "slashgear.com",
    "pocket-lint.com", "trustedreviews.com", "whathifi.com", "stuff.tv",
    "pcgamer.com", "eurogamer.net", "ign.com", "gamespot.com", "polygon.com",
    "tweaktown.com", "techpowerup.com", "anandtech.com", "hardwarecanucks.com",
    "overclockers.co.uk", "guru3d.com", "phoronix.com", "extremetech.com",
    "techspot.com", "notebookcheck.net", "liliputing.com", "cnx-software.com",
    "neowin.net", "winbeta.org", "thurrott.com", "petapixel.com", "dpreview.com",
    "imaging-resource.com", "thephoblographer.com", "canonrumors.com",
    "fujirumors.com", "sonyalpharumors.com", "43rumors.com", "photorumors.com",

    # Gaming & Entertainment
    "comicbook.com", "screenrant.com", "variety.com", "hollywoodreporter.com",
    "deadline.com", "thewrap.com", "indiewire.com", "collider.com", "slashfilm.com",
    "darkhorizons.com", "comingsoon.net", "denofgeek.com", "bleedingcool.com",
    "newsarama.com", "cbr.com", "kotaku.com", "destructoid.com", "shacknews.com",
    "siliconera.com", "gematsu.com", "vg247.com", "videogamer.com", "pushsquare.com",
    "nintendolife.com", "purexbox.com", "vgc.com", "fanbyte.com", "rockpapershotgun.com",

    # Lifestyle & General News
    "dailymail.com", "dailymail.co.uk", "nypost.com", "foxnews.com", "cnn.com",
    "nbcnews.com", "abcnews.go.com", "cbsnews.com", "reuters.com", "apnews.com",
    "bloomberg.com", "forbes.com", "fortune.com", "businessinsider.com",
    "wsj.com", "nytimes.com", "theguardian.com", "telegraph.co.uk", "independent.co.uk",
    "bbc.com", "bbc.co.uk", "aljazeera.com", "ndtv.com", "indiatimes.com",
    "economictimes.indiatimes.com", "thehindu.com", "yahoo.com", "sports.yahoo.com",
    "robbreport.com", "gentlemansjournal.com", "gq.com", "esquire.com",
    "vogue.com", "hypebeast.com", "highsnobiety.com", "inputmag.com",
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
    len1, len2 = len(text1), len(text2)
    if abs(len1 - len2) > max(len1, len2) * 0.2:
        return False
    ratio = difflib.SequenceMatcher(None, text1[:1000], text2[:1000]).ratio()
    return ratio > 0.85


from app.shared.dto.ingestion import ClassifiedItemDTO, EnrichedItemDTO


# ── PHASE 1: DISCOVERY ENRICHMENT (Lightweight / All Content Types) ───────────

def normalize_ingested_data(item: Any) -> EnrichedItemDTO:
    """
    Standardizes and sanitizes raw metadata from discovery APIs.
    Used for ALL content types (Articles, Videos, Posts).
    Performs NO network calls.
    """
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    
    # 1. Basic Sanitization
    content_raw = data.get("content", "") or data.get("description", "")
    if content_raw:
        norm = normalize_content(content_raw, data.get("description", ""))
        data.update({
            "content_html":  norm["content_html"],
            "content_text":  norm["content_text"],
            "word_count":    norm["word_count"],
            "quality_score": score_content_quality(norm["content_html"], norm["content_text"]),
            "content":       norm["content_html"], # Backwards compatibility
        })
    
    # Ensure mandatory fields exist
    data.setdefault("is_content_scraped", False)
    data.setdefault("content_source", "api")
    
    return EnrichedItemDTO(**data)


def ingest_enrichment_router(item: ClassifiedItemDTO) -> EnrichedItemDTO:
    """
    Entry point for Phase 1 Ingestion.
    Ensures discovery is lightning fast by only performing local normalization.
    """
    url = (item.url or "").lower()
    title = (item.title or "")[:60]

    # Passthrough for non-article types or specific platforms if needed
    if "youtube.com" in url or "reddit.com" in url:
        return normalize_ingested_data(item)

    return normalize_ingested_data(item)


# ── PHASE 2: HEAVY ENRICHMENT (Scraping / Articles Only) ──────────────────────

def full_article_scraping_pipeline(item: Any) -> EnrichedItemDTO:
    """
    Entry point for Phase 2 Background Worker.
    Performs heavy network-based enrichment (Scraping, Extractor APIs).
    Targets only Articles.
    """
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    url = data.get("url", "")
    description = data.get("description", "")
    
    if not url:
        return normalize_ingested_data(item)

    log_integration_start(logger, _NAME, mode="phase_2_heavy", url=url[:80])
    
    candidates = []
    trusted = is_trusted(url)

    # 1. Candidate: API/Initial Content (Local)
    initial_content = data.get("content", "")
    if initial_content:
        norm = normalize_content(initial_content, None)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append({
            "content_html": norm["content_html"], "content_text": norm["content_text"],
            "word_count": norm["word_count"], "quality_score": score,
            "is_content_scraped": False, "content_source": "api",
        })

    # 2. Candidate: Extractor APIs
    best_existing_wc = candidates[0]["word_count"] if candidates else 0
    if trusted or best_existing_wc < 200:
        extractor_result = extract_with_apis(url)
        if extractor_result:
            candidates.append({
                "content_html": extractor_result["content_html"],
                "content_text": extractor_result["content_text"],
                "image_url":    extractor_result.get("image_url"),
                "word_count":   extractor_result["word_count"],
                "quality_score": extractor_result["quality_score"],
                "is_content_scraped": False, "content_source": extractor_result["source"],
            })

    # 3. Candidate: Scraper (Playwright)
    best_wc_so_far = max((c["word_count"] for c in candidates), default=0)
    if trusted or best_wc_so_far < 150:
        try:
            log_scrape_start(logger, url)
            scraped_html = scrape_article_content(url)
            if scraped_html:
                norm = normalize_content(scraped_html, None)
                score = score_content_quality(norm["content_html"], norm["content_text"])
                candidates.append({
                    "content_html": norm["content_html"], "content_text": norm["content_text"],
                    "word_count": norm["word_count"], "quality_score": score,
                    "is_content_scraped": True, "content_source": "scraper",
                })
                log_scrape_success(logger, url, words=norm["word_count"], source="scraper")
        except Exception as e:
            log_scrape_error(logger, url, reason=str(e))

    # 4. Fallback (Local)
    if not candidates and description:
        norm = normalize_content(text_to_html(description), description)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append({
            "content_html": norm["content_html"], "content_text": norm["content_text"],
            "word_count": norm["word_count"], "quality_score": score,
            "is_content_scraped": False, "content_source": "fallback",
        })

    # 5. Final Selection & Metadata Recovery
    if candidates:
        best_candidate = max(candidates, key=lambda c: c["quality_score"])
    else:
        return normalize_ingested_data(item)

    selected_image = data.get("image_url")
    canonical_url = data.get("canonical_url")
    
    # Metadata Recovery (HEAD/Lightweight Scrape)
    if not selected_image or not canonical_url:
        recovered = recover_article_metadata(url)
        if not selected_image:
            selected_image = best_candidate.get("image_url") or recovered.get("image_url")
        if not canonical_url:
            canonical_url = recovered.get("canonical_url")

    # Update state
    data.update(best_candidate)
    data.update({
        "image_url": selected_image,
        "canonical_url": canonical_url,
        "content": best_candidate["content_html"],
    })

    log_integration_success(
        logger, _NAME, items=1, source=best_candidate["content_source"],
        score=f"{best_candidate['quality_score']:.3f}", words=best_candidate["word_count"],
        mode="phase_2_full"
    )
    return EnrichedItemDTO(**data)
