"""
Normalizer Package — Public API
---------------------------------
Single entry point for the full markdown normalization pipeline.

Usage:
    from app.application.content.ingestion.normalizer import normalize_markdown

    result = normalize_markdown(
        raw_markdown,
        source_url="https://www.artofmanliness.com/...",
        hero_image_url=article.image_url,
    )
    clean_md       = result["content_markdown"]
    content_blocks = result["content_blocks"]   # None if quality gate failed
    approved_imgs  = result["extracted_images"]
    stats          = result["stats"]             # diagnostic dict

Stages:
    1. Preprocess   — strip alt text, citations, collapse blank lines
    2. Junk removal — truncate at footers, strip nav/audio/social/logo,
                      strip lines whose links point exclusively to the source domain
    3. Image normalization — filter chrome images, keep approved article images
    4. Block parsing — convert clean MD to content_blocks list, detect embeds,
                       attach captions to images
    5. Validation   — garbage removal, deduplication, paragraph merging, quality gate
"""
import logging
import time
from typing import Optional
from urllib.parse import urlparse
from . import (
    stage_0_html_pruning,
    stage_1_preprocess,
    stage_2_junk_removal,
    stage_3_image_normalization,
    stage_4_block_parser,
    stage_5_validation,
)

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    """Return the bare hostname without 'www.' prefix, e.g. 'artofmanliness.com'."""
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def normalize_markdown(
    raw_md: str,
    source_url: Optional[str] = None,
    hero_image_url: Optional[str] = None,
) -> dict:
    """
    Run all 5 normalizer stages on the raw markdown.

    Parameters:
        raw_md          — raw markdown returned by the extractor service
        source_url      — full URL of the article (used to reject same-domain links)
        hero_image_url  — hero image already shown in the article header (excluded
                          from content_blocks to avoid duplication)

    Returns a dict with keys:
        content_markdown  — cleaned markdown text (permanent debugging artifact)
        content_blocks    — structured block list, or None if validation failed
        extracted_images  — list of approved image URLs found in the content
        stats             — diagnostic dict with block counts and processing info
    """
    t_start = time.monotonic()

    if not raw_md:
        return {
            "content_markdown": "",
            "content_blocks":   None,
            "extracted_images": [],
            "stats": {"input_chars": 0, "quality_gate_passed": False},
        }

    source_domain = _extract_domain(source_url)

    # Stage 0 — Structural block-level pruning (UI containers, orphan headings)
    md = stage_0_html_pruning.run(raw_md, source_domain=source_domain)

    # Stage 1 — Light preprocessing
    md = stage_1_preprocess.run(md)
    chars_after_stage1 = len(md)

    # Stage 2 — Junk section removal (also strips same-domain-only link lines)
    md, truncation_trigger = stage_2_junk_removal.run_with_stats(md, source_domain=source_domain)
    chars_after_stage2 = len(md)

    # Stage 3 — Image normalization (modifies md in place, returns approved set)
    md, approved_images = stage_3_image_normalization.run(md, hero_image_url=hero_image_url)

    # Stage 1 again: re-collapse blank lines after all removals
    md = stage_1_preprocess._collapse_blank_lines(md)

    # Stage 4 — Block parsing
    raw_blocks = stage_4_block_parser.run(
        md,
        approved_images=approved_images,
        source_domain=source_domain,
    )

    # Stage 5 — Validation with stats
    content_blocks, s5_stats = stage_5_validation.run_with_stats(
        raw_blocks,
        source_domain=source_domain,
    )

    elapsed_ms = int((time.monotonic() - t_start) * 1000)

    stats = {
        "input_chars":         len(raw_md),
        "chars_after_preprocess": chars_after_stage1,
        "chars_after_junk":    chars_after_stage2,
        "images_approved":     len(approved_images),
        "raw_blocks":          len(raw_blocks),
        "truncated_at":        truncation_trigger,
        "elapsed_ms":          elapsed_ms,
        **s5_stats,
    }

    # Single structured log line for every article processed
    logger.debug(
        "[normalizer] source=%s  blocks=%d  paragraphs=%d  images=%d  prices=%d  dates=%d  "
        "words=%d  nav_removed=%d  garbage=%d  orphans=%d  dedup=%d  merged=%d  gate=%s  ms=%d  truncated=%s",
        source_domain or "?",
        stats.get("output_blocks", 0),
        stats.get("paragraphs",    0),
        stats.get("images",        0),
        stats.get("prices",        0),
        stats.get("dates",         0),
        stats.get("total_words",   0),
        stats.get("nav_removed",   0),
        stats.get("garbage_removed", 0),
        stats.get("orphan_removed", 0),
        stats.get("dedup_removed", 0),
        stats.get("paragraphs_merged", 0),
        "PASS" if stats.get("quality_gate_passed") else "FAIL",
        elapsed_ms,
        "yes" if truncation_trigger else "no",
    )

    return {
        "content_markdown":  md.strip(),
        "content_blocks":    content_blocks,
        "extracted_images":  list(approved_images),
        "stats":             stats,
    }
