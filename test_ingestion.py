from dotenv import load_dotenv
load_dotenv()

from main import app
from app.jobs.tasks.content.videos import run_youtube_fetch
from app.jobs.tasks.content.articles import run_newsapi_fetch, run_gnews_fetch, run_rss_fetch
from app.jobs.tasks.content.posts import run_reddit_fetch
from app.domains.content.models import Article, Video

with app.app_context():
    print("\n--- Running YouTube Ingestion ---")
    run_youtube_fetch(limit=1)

    print("\n--- Running Reddit Ingestion ---")
    run_reddit_fetch(limit=1)

    print("\n--- Running NewsAPI Ingestion ---")
    run_newsapi_fetch(limit=1)

    print("\n--- Running GNews Ingestion ---")
    run_gnews_fetch(limit=1)

    print("\n--- Running RSS Ingestion ---")
    run_rss_fetch(limit=1)

    print("\n--- Checking Database ---")
    # Check Video Integrity
    v = Video.query.order_by(Video.id.desc()).first()
    if v:
        print(f"Video: {v.title} | Channel: {v.channel_name} | Platform: {v.platform}")
    else:
        print("No videos found.")

    # Check Article Integrity
    a = Article.query.order_by(Article.id.desc()).first()
    if a:
        print(f"Article: {a.title} | Source: {a.source_name}")
        print(f"Content HTML length: {len(a.content_html) if a.content_html else 0}")
        print(f"Legacy Content length: {len(a.body) if a.body else 0}")
        print(f"Quality Score: {a.quality_score}")
        print(f"Published: {a.published_at}")
    else:
        print("No articles found.")
