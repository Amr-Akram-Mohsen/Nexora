from ..core.run_fetcher import run_fetcher


def run_youtube_fetch():
    return run_fetcher(
        source_name="youtube",
        object_type="video",
        api_key_name="YOUTUBE_API_KEY",
    )


def run_newsapi_ai_fetch():
    return run_fetcher(
        source_name="newsapi_ai",
        object_type="article",
        api_key_name="NEWSAPI_AI_API_KEY",
    )

