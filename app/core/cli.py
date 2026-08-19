# app/core/cli.py
from app.integrations.content.runners import (
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
        from app.domains.recommendation.service.matcher import match_articles_to_items

        app.logger.info("Starting content-to-product matcher...")
        count = match_articles_to_items()
        app.logger.info("Matcher complete! Created %d new links.", count)





    @app.cli.command("fetch-youtube")
    def fetch_youtube_command():
        run_youtube_fetch()

    @app.cli.command("fetch-newsapi-ai")
    def fetch_newsapi_ai_command():
        run_newsapi_ai_fetch()

    @app.cli.command("fetch-events")
    def fetch_events_command():
        """Hydrates incomplete Events from NewsAPI AI."""
        from app.application.content.workflows.event_hydration import run_event_hydration
        run_event_hydration(limit=100)



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
        results = enrich_discovered_articles(limit=50, force=force)
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
        from app.integrations.content.enrichment.taxonomy_enrichment import enrich_entities
        from app.domains.content.service.command import apply_relationships

        app.logger.info("Starting taxonomy enrichment for existing videos...")
        videos = Video.query.all()
        updated_count = 0

        for video in videos:
            # Extract entities using the new keyword extractor
            concepts = enrich_entities(video.title or "", video.description or "", [])
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

    @app.cli.command("geocode-locations")
    def geocode_locations_command():
        """Geocodes locations missing coordinates via Nominatim."""
        import requests
        import time
        from app.core.extensions import db
        from app.domains.taxonomy.models import Location

        locations = Location.query.filter((Location.latitude == None) | (Location.longitude == None)).all()
        total = len(locations)
        if total == 0:
            app.logger.info("All locations are already geocoded.")
            return

        app.logger.info("Starting geocoding for %d locations...", total)
        headers = {"User-Agent": "Nexora/1.0 (contact@nexora.com)"}
        success = 0
        failed = 0

        for i, loc in enumerate(locations):
            query = f"{loc.name}"
            if loc.country_name and loc.country_name.lower() not in query.lower():
                query = f"{loc.name}, {loc.country_name}"

            try:
                url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&format=json&limit=1"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        loc.latitude = float(data[0]["lat"])
                        loc.longitude = float(data[0]["lon"])
                        success += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception as e:
                app.logger.error("Error geocoding %s: %s", loc.name, e)
                failed += 1

            if i % 50 == 0:
                db.session.commit()
            time.sleep(1)

        db.session.commit()
        app.logger.info("Geocoding complete. Success: %d, Failed: %d", success, failed)

    @app.cli.command("seed-mock-coordinates")
    def seed_mock_coordinates_command():
        """Seeds rough coordinates for testing the globe/maps visualization."""
        import random
        from app.core.extensions import db
        from app.domains.taxonomy.models import Location

        known_locs = {
            "united states": (37.0902, -95.7129),
            "uk": (55.3781, -3.4360),
            "london": (51.5074, -0.1278),
            "paris": (48.8566, 2.3522),
            "france": (46.2276, 2.2137),
            "germany": (51.1657, 10.4515),
            "japan": (36.2048, 138.2529),
            "tokyo": (35.6762, 139.6503),
            "india": (20.5937, 78.9629),
            "china": (35.8617, 104.1954),
            "australia": (-25.2744, 133.7751),
            "canada": (56.1304, -106.3468),
            "brazil": (-14.2350, -51.9253),
            "russia": (61.5240, 105.3188),
            "egypt": (26.8206, 30.8025),
            "south africa": (-30.5595, 22.9375),
        }

        locations = Location.query.all()
        count = 0
        for loc in locations:
            name_lower = loc.name.lower()
            if name_lower in known_locs:
                loc.latitude = known_locs[name_lower][0]
                loc.longitude = known_locs[name_lower][1]
                count += 1
            elif random.random() < 0.1:
                loc.latitude = random.uniform(-60, 60)
                loc.longitude = random.uniform(-180, 180)
                count += 1

        db.session.commit()
        app.logger.info("Mocked %d coordinates for testing.", count)

