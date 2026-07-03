#!/usr/bin/env python
"""
inspect_blocks.py — Article Normalization Debug Inspector
----------------------------------------------------------
A TEMPORARY debugging script. Safe to delete after testing.

Usage (from project root):
    # Inspect the next 10 articles with markdown but no blocks
    python scripts/inspect_blocks.py

    # Inspect a specific article by ID (generates blocks if missing)
    python scripts/inspect_blocks.py --id 15052

    # Inspect multiple specific IDs
    python scripts/inspect_blocks.py --id 15052 --id 14987

    # Inspect N articles from the markdown-only queue
    python scripts/inspect_blocks.py --limit 5

    # Show all blocks (not just first/last)
    python scripts/inspect_blocks.py --id 15052 --full

    # Dry-run: never write back to database
    python scripts/inspect_blocks.py --limit 5 --no-save

NOTE: This script reuses _parse_blocks_from_markdown() from
      app/application/content/workflows/enrichment.py — the same
      function that `flask enrich-articles` uses in its local re-parse pass.
      It does NOT call external APIs.
"""
import sys
import os
import json
import textwrap
import argparse
from collections import Counter
from datetime import datetime

# Force UTF-8 output on Windows so box-drawing chars and emoji render correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Bootstrap Flask app context ───────────────────────────────────────────────
# Add the project root to sys.path so imports resolve the same way as Flask does.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core import create_app
app = create_app()

# ── ANSI colour helpers ───────────────────────────────────────────────────────
def _c(text, code): return f"\033[{code}m{text}\033[0m"
def bold(t):    return _c(t, "1")
def cyan(t):    return _c(t, "96")
def green(t):   return _c(t, "92")
def yellow(t):  return _c(t, "93")
def red(t):     return _c(t, "91")
def dim(t):     return _c(t, "2")
def magenta(t): return _c(t, "95")

SEP  = "-" * 80
SEP2 = "=" * 80

# ── Known publisher UI strings that should NOT survive normalization ──────────
SUSPICIOUS_PHRASES = [
    "related stories", "related articles", "related posts", "related content",
    "more from", "you may also like", "you may like", "recommended for you",
    "read next", "see also", "editor's picks", "most popular", "trending",
    "leave a reply", "leave a comment", "post a comment", "add a comment",
    "join the discussion", "be the first to comment",
    "advertisement", "sponsored", "partner content",
    "newsletter", "subscribe", "sign up", "never miss",
    "comments", "loading comments", "no comments yet",
    "cookie policy", "privacy policy",
    "about the author", "follow us",
    "table of contents", "in this article",
    "share this", "tweet this",
    "back to top",
    "register", "email address", "stay informed", "get updates",
    "allow notifications", "browser preferences", "yes please", "not now",
    "copy link", "facebook", "twitter", "linkedin", "addtoany",
    "open image", "expand image", "view gallery", "load more",
    "has been writing", "covers", "staff writer", "follow author", "bio",
    "join us on reddit", "discord", "telegram",
    "you may also like", "next article", "previous article"
]

# ── Block types ───────────────────────────────────────────────────────────────
KNOWN_TYPES = {"paragraph", "heading", "image", "quote", "list", "table", "code", "embed", "divider", "price", "date"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Quick tag stripper for analysis (not for rendering)."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _block_preview(block: dict, max_chars: int = 120) -> str:
    """One-line human-readable summary of a block."""
    btype = block.get("type", "?")
    if btype == "paragraph":
        text = _strip_html(block.get("text", ""))
        return f"[paragraph]  {text[:max_chars]}{'…' if len(text) > max_chars else ''}"
    elif btype == "heading":
        return f"[h{block.get('level','?')}]       {_strip_html(block.get('text', ''))}"
    elif btype == "image":
        url = block.get("url", "")
        cap = block.get("caption") or ""
        return f"[image]     {url[:70]}{'…' if len(url) > 70 else ''}  caption={bool(cap)}"
    elif btype == "list":
        items = block.get("items", [])
        return f"[list {'ol' if block.get('ordered') else 'ul'}]    {len(items)} items  first=«{_strip_html(items[0])[:60] if items else ''}»"
    elif btype == "quote":
        return f"[quote]     {_strip_html(block.get('text', ''))[:max_chars]}"
    elif btype == "table":
        rows = block.get("rows", [])
        return f"[table]     {len(rows)} rows × {len(rows[0]) if rows else 0} cols"
    elif btype == "code":
        return f"[code/{block.get('language','?')}]  {block.get('text','')[:60]}"
    elif btype == "embed":
        return f"[embed:{block.get('provider','?')}]  {block.get('url','')[:70]}"
    elif btype == "divider":
        return "[divider]"
    else:
        return f"[{btype}]  {str(block)[:100]}"


def _check_suspicious(block: dict) -> list[str]:
    """Return a list of warnings if block text looks like publisher UI."""
    btype = block.get("type")
    warnings = []
    if btype in ("paragraph", "heading", "quote"):
        raw = _strip_html(block.get("text", "")).lower().strip()
        for phrase in SUSPICIOUS_PHRASES:
            if raw == phrase or raw.startswith(phrase + " ") or raw.endswith(" " + phrase):
                warnings.append(f"Suspicious UI text: «{raw[:80]}»")
                break
    elif btype == "list":
        for item in block.get("items", []):
            raw = _strip_html(item).lower().strip()
            for phrase in SUSPICIOUS_PHRASES:
                if raw == phrase:
                    warnings.append(f"Suspicious list item: «{raw}»")
                    break
    return warnings


def _sanity_check(blocks: list[dict]) -> list[str]:
    """Run all sanity checks on a block list. Returns list of warning strings."""
    issues = []
    seen_texts = []

    for i, block in enumerate(blocks):
        btype = block.get("type", "MISSING")
        label = f"Block #{i} ({btype})"

        # Unknown type
        if btype not in KNOWN_TYPES:
            issues.append(f"{label}: ❌ UNKNOWN block type")

        # Empty / whitespace-only paragraph
        if btype == "paragraph":
            raw = _strip_html(block.get("text", "")).strip()
            if not raw:
                issues.append(f"{label}: ⚠  Empty paragraph")
            elif raw == raw.upper() and len(raw) < 30:
                issues.append(f"{label}: ⚠  All-caps short text (possible label/button): «{raw}»")
            
            # Check for empty markdown links
            import re
            if re.search(r'\[\s*\]\([^)]+\)', block.get("text", "")):
                issues.append(f"{label}: ⚠  Contains empty markdown link [](url) - possibly malformed image")

            # Check for target="_blank" malformed HTML
            if re.search(r'target=".*?blank"?', block.get("text", "")):
                issues.append(f"{label}: ⚠  Contains malformed HTML attribute (target=_blank)")

            # Check for Image credit
            if re.search(r'^\(?(?:Image|Photo)\s+(?:credit|by):.*?\)?\s*$', raw, re.IGNORECASE):
                issues.append(f"{label}: ⚠  Paragraph looks like an isolated image credit")

        # Heading without text
        if btype == "heading" and not _strip_html(block.get("text", "")).strip():
            issues.append(f"{label}: ❌ Heading with no text")

        # Image without URL
        if btype == "image":
            if not block.get("url"):
                issues.append(f"{label}: ❌ Image block missing URL")
            if block.get("alt") == "" and not block.get("caption"):
                issues.append(f"{label}: ⚠  Image has no alt text and no caption")

        # Duplicate consecutive blocks
        if btype in ("paragraph", "heading") and i > 0:
            prev = blocks[i - 1]
            if prev.get("type") == btype:
                curr_text = _strip_html(block.get("text", "")).lower()
                prev_text = _strip_html(prev.get("text", "")).lower()
                if curr_text == prev_text:
                    issues.append(f"{label}: ⚠  Exact duplicate of block #{i-1}")

        # Suspicious publisher UI
        sus = _check_suspicious(block)
        for w in sus:
            issues.append(f"{label}: 🚨 {w}")

        # List with no items
        if btype == "list" and not block.get("items"):
            issues.append(f"{label}: ❌ Empty list block")

    return issues


def _count_types(blocks: list[dict]) -> dict:
    counts = Counter(b.get("type", "unknown") for b in blocks)
    # also count images that have captions
    counts["image_with_caption"] = sum(
        1 for b in blocks if b.get("type") == "image" and b.get("caption")
    )
    return dict(counts)


# ── Core inspector ────────────────────────────────────────────────────────────

def inspect_article(article, save: bool = True, full: bool = False, peek: int = 3):
    """
    Inspect one Article object.
    - If content_blocks is already populated: inspect existing blocks.
    - If not: call _parse_blocks_from_markdown (no network) to generate, then inspect.
    """
    from app.application.content.workflows.enrichment import _parse_blocks_from_markdown
    from app.core.extensions import db

    generated_now = False
    issues        = []

    print()
    print(SEP2)
    print(bold(f"  Article #{article.id}"))
    print(SEP2)
    print(f"  {bold('Title')}:  {article.title}")
    print(f"  {bold('Source')}: {article.source_name or '?'}")
    print(f"  {bold('URL')}:    {article.url or '?'}")
    print(f"  {bold('Status')}: {article.status or '?'}")
    print(f"  {bold('Scraped')}: {article.is_content_scraped}")
    print(f"  {bold('Words')}: {article.word_count or 0}")

    # ── Resolve blocks ────────────────────────────────────────────────────
    if article.content_blocks:
        blocks = article.content_blocks
        print(f"  {bold('Blocks source')}: {green('already in database')}")
    elif article.content_markdown:
        print(f"  {bold('Blocks source')}: {yellow('generating from content_markdown (no network)')}...")
        ok = _parse_blocks_from_markdown(article)
        if ok and article.content_blocks:
            blocks = article.content_blocks
            generated_now = True
            if save:
                db.session.commit()
                print(f"  {dim('Saved to database.')}")
            else:
                db.session.rollback()
                print(f"  {dim('(dry run — not saved)')}")
        else:
            blocks = []
            print(f"  {red('⚠  Normalization produced no valid blocks (quality gate failed).')}")
    else:
        blocks = []
        print(f"  {red('⚠  No content_markdown and no content_blocks — nothing to inspect.')}")

    if not blocks:
        print(SEP)
        return

    # ── Block type summary ────────────────────────────────────────────────
    counts = _count_types(blocks)
    print()
    print(f"  {bold('Total blocks')}: {cyan(str(len(blocks)))}")
    print(f"  {bold('Block type breakdown')}:")
    for btype in ["paragraph", "heading", "image", "image_with_caption",
                  "quote", "list", "table", "code", "embed", "divider", "unknown"]:
        n = counts.get(btype, 0)
        if n > 0:
            bar = "█" * min(n, 30)
            print(f"    {btype:<22} {str(n):>4}  {dim(bar)}")

    # ── First N blocks ────────────────────────────────────────────────────
    preview_count = len(blocks) if full else min(peek, len(blocks))
    print()
    print(bold(f"  First {preview_count} block(s):"))
    for i, b in enumerate(blocks[:preview_count]):
        print(f"    [{i:02d}]  {_block_preview(b)}")

    if not full and len(blocks) > peek * 2:
        print(f"    {dim(f'… {len(blocks) - peek * 2} blocks in the middle …')}")
        print()
        print(bold(f"  Last {peek} block(s):"))
        for i, b in enumerate(blocks[-peek:], start=len(blocks) - peek):
            print(f"    [{i:02d}]  {_block_preview(b)}")
    elif not full and len(blocks) > peek:
        print()
        print(bold(f"  Last {len(blocks) - peek} block(s):"))
        for i, b in enumerate(blocks[peek:], start=peek):
            print(f"    [{i:02d}]  {_block_preview(b)}")

    # ── Detailed JSON for first + last blocks ─────────────────────────────
    if not full:
        sample_indices = list(range(min(peek, len(blocks))))
        if len(blocks) > peek:
            sample_indices += list(range(max(peek, len(blocks) - peek), len(blocks)))
        print()
        print(bold("  Full JSON of sampled blocks:"))
        for i in sample_indices:
            b = blocks[i]
            j = json.dumps(b, ensure_ascii=False, indent=2)
            indented = textwrap.indent(j, "    ")
            print(f"  {dim(f'--- block #{i} ---')}")
            print(indented)
    else:
        print()
        print(bold("  All blocks (full JSON):"))
        for i, b in enumerate(blocks):
            j = json.dumps(b, ensure_ascii=False, indent=2)
            print(f"  {dim(f'--- block #{i} ---')}")
            print(textwrap.indent(j, "    "))

    # ── Sanity checks ─────────────────────────────────────────────────────
    issues = _sanity_check(blocks)
    print()
    if issues:
        print(bold(red(f"  ⚠  Sanity check warnings ({len(issues)}):")))
        for w in issues:
            print(f"    {yellow('•')} {w}")
    else:
        print(green(f"  ✓  Sanity checks passed — no issues detected."))

    print()


# ── Summary reporter ──────────────────────────────────────────────────────────

def print_summary(results: list[dict]):
    print()
    print(SEP2)
    print(bold("  INSPECTION SUMMARY"))
    print(SEP2)
    total = len(results)
    had_blocks    = sum(1 for r in results if r["had_blocks"])
    generated     = sum(1 for r in results if r["generated"])
    gate_failed   = sum(1 for r in results if r["gate_failed"])
    had_issues    = sum(1 for r in results if r["issue_count"] > 0)
    total_issues  = sum(r["issue_count"] for r in results)

    print(f"  Articles inspected : {cyan(str(total))}")
    print(f"  Already had blocks : {green(str(had_blocks))}")
    print(f"  Generated now      : {yellow(str(generated))}")
    print(f"  Quality gate FAIL  : {red(str(gate_failed))}")
    print(f"  Articles w/ issues : {red(str(had_issues))} ({total_issues} total warnings)")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inspect article normalization / content_blocks quality.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--id",    type=int, action="append", dest="ids",
                        metavar="ARTICLE_ID",
                        help="Inspect a specific article ID (can be repeated).")
    parser.add_argument("--limit", type=int, default=10,
                        help="Max articles to inspect from the markdown-only queue (default 10).")
    parser.add_argument("--full",  action="store_true",
                        help="Print every block in full instead of first/last peek.")
    parser.add_argument("--peek",  type=int, default=3,
                        help="Number of blocks to show at the start and end (default 3).")
    parser.add_argument("--no-save", action="store_true",
                        help="Dry run: generate blocks for display but do NOT write to database.")
    args = parser.parse_args()

    save = not args.no_save

    with app.app_context():
        from app.domains.content.models import Article
        from app.domains.content.service.query.filtering import (
            get_markdown_only_articles,
        )

        results = []

        if args.ids:
            # Specific article IDs requested
            articles = []
            for aid in args.ids:
                a = Article.query.filter_by(id=aid).first()
                if a:
                    articles.append(a)
                else:
                    print(red(f"Article #{aid} not found in database."))
        else:
            # Pull from the markdown-only queue (no blocks yet, has markdown)
            articles = get_markdown_only_articles(args.limit)
            if not articles:
                # Also try articles that already have blocks for inspection
                print(yellow("No markdown-only articles found. Fetching articles with existing blocks..."))
                articles = Article.query.filter(
                    Article.content_blocks.isnot(None)
                ).limit(args.limit).all()

        if not articles:
            print(red("No articles to inspect."))
            return

        print()
        print(SEP2)
        print(bold(f"  Nexora — Block Inspector  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"))
        print(bold(f"  Inspecting {len(articles)} article(s)  |  save={save}  |  full={args.full}"))
        print(SEP2)

        for article in articles:
            had_blocks  = bool(article.content_blocks)
            gate_failed = False
            issue_count = 0

            inspect_article(article, save=save, full=args.full, peek=args.peek)

            if not article.content_blocks:
                gate_failed = True
            else:
                issues      = _sanity_check(article.content_blocks)
                issue_count = len(issues)

            results.append({
                "id":         article.id,
                "had_blocks": had_blocks,
                "generated":  not had_blocks and bool(article.content_blocks),
                "gate_failed": gate_failed,
                "issue_count": issue_count,
            })

        print_summary(results)


if __name__ == "__main__":
    main()
