import logging
from .articles import run_newsapi_fetch, run_gnews_fetch, run_rss_fetch
from .videos import run_youtube_fetch
from .posts import run_reddit_fetch

logger = logging.getLogger(__name__)

def run_content_fetch(limit: int | None = None):
    """Fetch all active content sources and return a summary report."""
    print("\n" + "="*50)
    print("NEXORA GLOBAL DISCOVERY ENGINE STARTED")
    if limit:
        print(f"TEST MODE ENABLED: Capping at {limit} queries per source")
    print("="*50 + "\n")

    results = {
        "newsapi": run_newsapi_fetch(limit=limit),
        "gnews": run_gnews_fetch(limit=limit),
        "youtube": run_youtube_fetch(limit=limit),
        "rss": run_rss_fetch(limit=limit),
        "reddit": run_reddit_fetch(limit=limit)
    }
    
    print("\n" + "="*50)
    print("🏁 DISCOVERY COMPLETE - SUMMARY REPORT")
    print("="*50)
    for source, res in results.items():
        status = res.get("status", "error").upper()
        count = res.get("count", 0)
        print(f" - {source.ljust(10)}: {status} ({count} new contents)")
    print("="*50 + "\n")

    logger.info(f"[Runner] Complete! Summary: {results}")
    return results

