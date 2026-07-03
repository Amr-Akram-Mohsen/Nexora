# app/core/cli.py
from app.integrations.content.fetcher_runners.all_contents import (
    run_newsapi_fetch,
    run_gnews_fetch,
    run_youtube_fetch,
    run_reddit_fetch,
    run_rss_fetch,
    run_content_fetch,
)
# from app.integrations.content.fetcher_runners.rss import run_rss_fetch
# from app.integrations.content.fetcher_runners.all_contents import run_content_fetch


def register_commands(app):
    """
    Registers custom Flask CLI commands for database seeding,
    content ingestion, and system maintenance.
    """

    @app.cli.command("seed-db")
    def seed_db_command():
        from scripts.seed import seed_db

        seed_db()
        app.logger.info("Database seeded successfully!")

    @app.cli.command("link-contents")
    def link_contents_command():
        from app.application.recommendation.matcher import match_articles_to_items

        app.logger.info("Starting content-to-item matcher...")
        count = match_articles_to_items()
        app.logger.info("Matcher complete! Created %d new links.", count)

    @app.cli.command("seed-noon-stores")
    def seed_noon_stores_command():
        """Seed Noon/Namshi store records for ArabClicks affiliate network."""
        from app.integrations.ecommerce.core.noon import seed_arabclicks_stores

        created = seed_arabclicks_stores()
        app.logger.info("Done! %d new ArabClicks stores seeded.", created)

    @app.cli.command("fetch-newsapi")
    def fetch_newsapi_command():
        run_newsapi_fetch()

    @app.cli.command("fetch-gnews")
    def fetch_gnews_command():
        run_gnews_fetch()

    @app.cli.command("fetch-rss")
    def fetch_rss_command():
        run_rss_fetch()

    @app.cli.command("fetch-youtube")
    def fetch_youtube_command():
        run_youtube_fetch()

    @app.cli.command("fetch-reddit")
    def fetch_reddit_command():
        run_reddit_fetch()

    @app.cli.command("fetch-all")
    def fetch_all_command():
        """Runs all active fetchers in one go."""
        app.logger.info("--- [1/2] Fetching Articles (RSS/NewsAPI/GNews/YouTube) ---")
        run_content_fetch()

    @app.cli.command("fetch-test")
    def fetch_test_command():
        """Runs a limited discovery run (5 queries per source) for testing."""
        app.logger.info("--- Starting Limited Test Run (5 queries/source) ---")
        run_content_fetch()

    import click
    @app.cli.command("enrich-articles")
    @click.option("--extractor", default="firecrawl", help="Extractor service to use (e.g. firecrawl, jina)")
    def enrich_articles_command(extractor):
        """Perform full-body scraping and quality-gated publication for pending articles."""
        from app.application.content.workflows.enrichment import (
            reprocess_unscraped_articles,
        )

        app.logger.info(f"Starting full-body enrichment using {extractor}...")
        count = reprocess_unscraped_articles(30, extractor_service=extractor)
        app.logger.info("Done! Successfully published %d articles.", count)

    @app.cli.command("init-content-status")
    def init_content_status_command():
        """Initialize status and is_published for existing content."""
        from app.domains.content.models import Article, Content
        from app.core.extensions import db

        app.logger.info("Initializing Article status...")
        articles = Article.query.all()
        for a in articles:
            if (a.content_text and len(a.content_text) > 200) or (
                a.body and len(a.body) > 200
            ):
                a.status = "complete"
            else:
                a.status = "pending"

            content_rec = Content.query.filter_by(
                object_type="article", object_id=a.id
            ).first()
            if content_rec:
                if a.status == "complete" and a.image_url:
                    content_rec.is_published = True
                else:
                    content_rec.is_published = False

        app.logger.info("Initializing Video/Post status...")
        Content.query.filter(Content.object_type.in_(["video", "post"])).update(
            {Content.is_published: True}, synchronize_session=False
        )

        db.session.commit()
        app.logger.info("Done!")

    @app.cli.command("generate-sitemap")
    def generate_sitemap_command():
        """Generate a static sitemap.xml file."""
        from app.application.system.sitemap import generate_static_sitemap

        app.logger.info("Generating sitemap...")
        count = generate_static_sitemap(app)
        app.logger.info("Done! Sitemap generated with %d URLs.", count)

    @app.cli.command("run-scheduler")
    def run_scheduler_command():
        """Run the background scheduler in a standalone process."""
        from app.integrations.scheduler import init_scheduler
        import time

        app.logger.info("Starting Nexora Background Scheduler...")
        init_scheduler(app)
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            app.logger.info("Scheduler stopping...")
