import logging
import difflib
from urllib.parse import urlparse
from app.integrations.content.article_utils.extract_article_content import scrape_article_content
from app.integrations.content.article_utils.extractor_clients import extract_with_apis
from app.integrations.content.article_utils.quality import score_content_quality
from app.integrations.content.article_utils.content_normalizer import normalize_content, text_to_html
from app.shared.utils.logging import (
    log_integration_start, log_integration_success, log_integration_error,
    log_integration_warning, log_scrape_start, log_scrape_success, log_scrape_error,
)

logger = logging.getLogger(__name__)

_NAME = "enrichment"

# ── Trusted sources (eligible for full-content scraping) ───────────────────────
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
    len1, len2 = len(text1), len(text2)
    if abs(len1 - len2) > max(len1, len2) * 0.2:
        return False
    ratio = difflib.SequenceMatcher(None, text1[:1000], text2[:1000]).ratio()
    return ratio > 0.85


from app.shared.dto.ingestion import ClassifiedItemDTO, EnrichedItemDTO


def route_enrichment_strategy(item: ClassifiedItemDTO, should_scrape: bool = False) -> EnrichedItemDTO:
    """
    Routes enrichment based on content source/type.
    Avoids scraping social-media domains directly.
    Always returns an EnrichedItemDTO (never None).

    Args:
        item:          Classified content item DTO.
        should_scrape: When True, enables full scraping pipeline.
                       Defaults to False (API content + fallback only).
    """
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    url = data.get("url", "").lower()
    title = data.get("title", "")[:60]

    try:
        if "youtube.com" in url or "reddit.com" in url:
            logger.info("[INTEGRATION][%s] route=passthrough  title=%s", _NAME, title)
            return EnrichedItemDTO(**data)

        logger.info(
            "[INTEGRATION][%s] route=article_enrichment  should_scrape=%s  title=%s",
            _NAME, should_scrape, title,
        )
        return enrich_article_content(item, should_scrape=should_scrape)

    except Exception as e:
        log_integration_error(logger, _NAME, e, title=title, exc_info=True)
        # Return a safe passthrough so the pipeline can still persist what it has
        return EnrichedItemDTO(**data)


def enrich_article_content(item: ClassifiedItemDTO, should_scrape: bool = False) -> EnrichedItemDTO:
    """
    Core content strategy layer.
    Evaluates API, Extractor, Scraper, and Fallback candidates.
    Selects the best result based on quality scoring.
    Always returns an EnrichedItemDTO.

    Args:
        item:          Classified content item DTO.
        should_scrape: When True, enables CloudScraper/Playwright scraping.
                       Defaults to False — API content + description fallback only.
    """
    data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    url = data.get("url", "")
    description = data.get("description", "")
    log_integration_start(logger, _NAME, url=url[:80], should_scrape=should_scrape)

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
            "word_count":   norm["word_count"],
            "quality_score": score,
            "is_content_scraped": False,
            "content_source": "api",
        })
        logger.info(
            "[INTEGRATION][%s] api_content  words=%d  score=%.3f  url=%s",
            _NAME, norm["word_count"], score, url[:80],
        )

    best_existing_wc = candidates[0]["word_count"] if candidates else 0
    extractor_failed = False

    # --- 2. Candidate: Extractor APIs ---
    if not is_youtube and (not initial_content or best_existing_wc < 200):
        if trusted or not initial_content:
            logger.info("[INTEGRATION][%s] trying extractor APIs  url=%s", _NAME, url[:80])
            extractor_result = extract_with_apis(url)
            if extractor_result:
                candidates.append({
                    "content_html": extractor_result["content_html"],
                    "content_text": extractor_result["content_text"],
                    "word_count":   extractor_result["word_count"],
                    "quality_score": extractor_result["quality_score"],
                    "is_content_scraped": False,
                    "content_source": extractor_result["source"],
                })
                logger.info(
                    "[INTEGRATION][%s] extractor success  source=%s  words=%d  url=%s",
                    _NAME, extractor_result["source"], extractor_result["word_count"], url[:80],
                )
            else:
                extractor_failed = True
                log_integration_warning(logger, _NAME, reason="extractor_no_result", url=url[:80])

    # --- 3. Candidate: Scraper (only when explicitly enabled) ---
    best_wc_so_far = max((c["word_count"] for c in candidates), default=0)

    if should_scrape and not is_youtube and (not initial_content or best_wc_so_far < 200):
        if trusted or extractor_failed:
            log_scrape_start(logger, url)
            try:
                scraped_html = scrape_article_content(url)
                if scraped_html:
                    norm = normalize_content(scraped_html, None)
                    score = score_content_quality(norm["content_html"], norm["content_text"])
                    candidates.append({
                        "content_html": norm["content_html"],
                        "content_text": norm["content_text"],
                        "word_count":   norm["word_count"],
                        "quality_score": score,
                        "is_content_scraped": True,
                        "content_source": "scraper",
                    })
                    log_scrape_success(logger, url, words=norm["word_count"], source="scraper")
                else:
                    log_scrape_error(logger, url, reason="no_content_extracted")
            except Exception as scrape_exc:
                log_scrape_error(logger, url, reason=f"{type(scrape_exc).__name__}: {scrape_exc}")
        else:
            logger.info(
                "[INTEGRATION][%s] scrape skipped  reason=not_trusted  url=%s", _NAME, url[:80]
            )
    elif not should_scrape and not is_youtube:
        logger.info(
            "[INTEGRATION][%s] scrape skipped  reason=should_scrape_false  url=%s", _NAME, url[:80]
        )

    # --- 4. Candidate: Description Fallback ---
    if description:
        norm = normalize_content(text_to_html(description), description)
        score = score_content_quality(norm["content_html"], norm["content_text"])
        candidates.append({
            "content_html": norm["content_html"],
            "content_text": norm["content_text"],
            "word_count":   norm["word_count"],
            "quality_score": score,
            "is_content_scraped": False,
            "content_source": "fallback",
        })

    # --- Deduplicate Candidates ---
    unique_candidates: list = []
    for c in candidates:
        is_duplicate = False
        for uc in unique_candidates:
            if _is_similar(c["content_text"], uc["content_text"]):
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
        logger.info("[INTEGRATION][%s] candidates evaluated:", _NAME)
        for c in candidates:
            logger.info(
                "[INTEGRATION][%s]   source=%-10s  score=%.3f  words=%d",
                _NAME, c["content_source"], c["quality_score"], c["word_count"],
            )
        best_candidate = max(candidates, key=lambda c: c["quality_score"])
        logger.info(
            "[INTEGRATION][%s] selected  source=%s  score=%.3f  words=%d",
            _NAME, best_candidate["content_source"],
            best_candidate["quality_score"], best_candidate["word_count"],
        )
    else:
        log_integration_warning(logger, _NAME, reason="no_candidates", url=url[:80])
        best_candidate = {
            "content_html": "",
            "content_text": "",
            "word_count": 0,
            "quality_score": 0.0,
            "is_content_scraped": False,
            "content_source": "fallback",
        }

    data.update(best_candidate)
    # For backwards compatibility and migration
    data["content"] = best_candidate["content_html"]

    log_integration_success(
        logger, _NAME, items=1,
        source=best_candidate["content_source"],
        score=f"{best_candidate['quality_score']:.3f}",
        words=best_candidate["word_count"],
    )
    return EnrichedItemDTO(**data)
