# app/core/cli.py
from app.integrations.content.fetcher_runners.all_contents import (
    run_youtube_fetch,
    run_content_fetch,
    run_newsapi_ai_fetch
)


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

        app.logger.info("Starting content-to-product matcher...")
        count = match_articles_to_items()
        app.logger.info("Matcher complete! Created %d new links.", count)

    @app.cli.command("seed-noon-stores")
    def seed_noon_stores_command():
        """Seed Noon/Namshi store records for ArabClicks affiliate network."""
        from app.integrations.ecommerce.core.noon import seed_arabclicks_stores

        created = seed_arabclicks_stores()
        app.logger.info("Done! %d new ArabClicks stores seeded.", created)



    @app.cli.command("fetch-youtube")
    def fetch_youtube_command():
        run_youtube_fetch()

    @app.cli.command("fetch-newsapi-ai")
    def fetch_newsapi_ai_command():
        run_newsapi_ai_fetch()



    @app.cli.command("fetch-all")
    def fetch_all_command():
        """Runs all active fetchers in one go."""
        app.logger.info("--- [1/2] Fetching Articles (NewsAPI_AI/YouTube) ---")
        run_content_fetch()

    @app.cli.command("fetch-test")
    def fetch_test_command():
        """Runs a limited discovery run (5 queries per source) for testing."""
        app.logger.info("--- Starting Limited Test Run (5 queries/source) ---")
        run_content_fetch()

    import click
    @app.cli.command("enrich-articles")
    @click.option("--force", is_flag=True, help="Ignore the 24-hour retry cooldown for failed articles")
    def enrich_articles_command(force):
        """Perform full-body scraping and quality-gated publication for pending articles."""
        from app.application.content.workflows.enrichment import (
            enrich_discovered_articles,
        )

        app.logger.info("Starting full-body enrichment using Diffbot...")
        results = enrich_discovered_articles(limit=5, force=force)
        count = results.get("published", 0)
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

    @app.cli.command("enrich-videos-taxonomy")
    def enrich_videos_taxonomy_command():
        """Retroactively extracts and assigns Brands & Topics to existing videos."""
        from app.domains.content.models import Video, Content
        from app.core.extensions import db
        from app.integrations.content.enrichment.taxonomy_enrichment import _enrich_entities
        from app.domains.content.service.command import apply_relationships

        app.logger.info("Starting taxonomy enrichment for existing videos...")
        videos = Video.query.all()
        updated_count = 0

        for video in videos:
            # Extract entities using the new keyword extractor
            concepts = _enrich_entities(video.title or "", video.description or "", [])
            if not concepts:
                continue

            # Get the Content wrapper
            content_rec = Content.query.filter_by(object_type="video", object_id=video.id).first()
            if not content_rec:
                continue

            # Apply relationships
            raw_data = {"er_concepts": concepts, "ingestion_method": "keyword_extractor"}
            apply_relationships(content_rec, raw_data, session=db.session)
            updated_count += 1
            
        db.session.commit()
        app.logger.info("Done! Enriched %d videos with Brands & Topics.", updated_count)

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
