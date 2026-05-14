from ..core.run_fetcher import run_fetcher


def run_newsapi_fetch():
    return run_fetcher(
        source_name="newsapi",
        object_type="article",
        api_key_name="NEWS_API_KEY",
    )


def run_gnews_fetch():
    return run_fetcher(
        source_name="gnews",
        object_type="article",
        api_key_name="GNEWS_API_KEY",
    )


def run_youtube_fetch():
    return run_fetcher(
        source_name="youtube",
        object_type="video",
        api_key_name="YOUTUBE_API_KEY",
    )


def run_reddit_fetch():
    return run_fetcher(
        source_name="reddit",
        object_type="post",
        api_key_name="REDDIT_CLIENT_ID",
    )
