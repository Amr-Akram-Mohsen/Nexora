# app/core/__init__.py
from flask import Flask
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from pathlib import Path
from config import Config
from .extensions import mail, csrf, limiter, cache, migrate, db
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv
load_dotenv()
from app.api.contents import bp as api_content_bp
from app.api.items import bp as api_item_bp
from app.api.users import bp as api_user_bp
from app.api.interactions import bp as api_interaction_bp
from app.api.stats import bp as api_dashboard_bp
from app.api.ingestions import bp as api_ingestion_bp


# from app.domains.dashboard.routes import bp as dashboard_bp

import app.domains.system
from app.domains.user.models import User
from app.web.routes import (
    admin_bp, user_bp, system_bp, content_bp, item_bp, interaction_bp, recommendation_bp, recommendation_bp
)


def setup_logging(app):
    """Configure rotating file logging for production-grade audit trails."""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # 10MB per file, keeping last 5 backups
    file_handler = RotatingFileHandler('logs/nexora.log', maxBytes=10240000, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    # Also ensure the standard python logger inherits this if needed
    logging.getLogger('app').addHandler(file_handler)

def create_app():
    base_dir = Path(__file__).resolve().parent  # app/core
    
    app = Flask(
        __name__,
        template_folder=str(base_dir.parent / "web" / "templates"),
        static_folder=str(base_dir.parent / "web" / "static")
    )

    if not app.debug:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config.from_object(Config)
    setup_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import domains

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'user.login'

    # Initialize Flask-Mail
    mail.init_app(app)

    # Initialize CSRF Protection
    csrf.init_app(app)

    # Initialize Cache
    cache.init_app(app)

    limiter.init_app(app)

    # Initialize OAuth
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    app.google = google

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(system_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(item_bp)
    app.register_blueprint(interaction_bp)
    app.register_blueprint(recommendation_bp)

    app.register_blueprint(api_content_bp)
    app.register_blueprint(api_item_bp)
    app.register_blueprint(api_user_bp)
    app.register_blueprint(api_interaction_bp)
    app.register_blueprint(api_dashboard_bp)
    app.register_blueprint(api_ingestion_bp)

    # app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    # ── Ensure api_models tables are created ─────────────────────
    from app.domains.external.models import LastAPIFetch, APIUsage  # noqa: F401

    @app.cli.command("seed-db")
    def seed_db_command():
        from scripts.seed import seed_db
        seed_db()
        print("Database seeded successfully!")

    @app.cli.command("link-contents")
    def link_contents_command():
        from app.domains.recommendation.matcher import match_contents_to_items
        print("Starting content-to-item matcher...")
        count = match_contents_to_items()
        print(f"Matcher complete! Created {count} new links.")

    @app.cli.command("seed-noon-stores")
    def seed_noon_stores_command():
        """Seed Noon/Namshi store records for ArabClicks affiliate network."""
        from app.integrations.ecommerce.noon import seed_arabclicks_stores
        created = seed_arabclicks_stores()
        print(f"Done! {created} new ArabClicks stores seeded.")

    @app.cli.command("fetch-newsapi")
    def fetch_newsapi_command():
        from app.jobs.tasks.content.articles import run_newsapi_fetch
        print("Fetching articles from NewsAPI...")
        run_newsapi_fetch()
        print("Done!")

    @app.cli.command("fetch-gnews")
    def fetch_gnews_command():
        from app.jobs.tasks.content.articles import run_gnews_fetch
        print("Fetching articles from GNews...")
        run_gnews_fetch()
        print("Done!")

    @app.cli.command("fetch-rss")
    def fetch_rss_command():
        from app.jobs.tasks.content.articles import run_rss_fetch
        print("Fetching articles from rss feeds...")
        run_rss_fetch()
        print("Done!")

    @app.cli.command("fetch-youtube")
    def fetch_youtube_command():
        from app.jobs.tasks.content.videos import run_youtube_fetch
        print("Fetching youtube reviews...")
        run_youtube_fetch()
        print("Done!")

    @app.cli.command("fetch-reddit")
    def fetch_reddit_command():
        from app.jobs.tasks.content.posts import run_reddit_fetch
        print("Fetching posts from Reddit communities...")
        run_reddit_fetch()
        print("Done!")

    @app.cli.command("fetch-all")
    def fetch_all_command():
        """Runs all active fetchers in one go."""
        from app.jobs.tasks.content.all_contents import (
            run_content_fetch, #run_reddit_fetch
        )
        # from app.jobs.tasks.content.fetch_items import (
        #     run_price_refresh, run_amazon_discovery, run_noon_discovery, run_arabclicks_price_refresh
        # )
        # from app.domains.recommendation.matcher import match_articles_to_items
        # Note: run_price_refresh and run_amazon_discovery might be in another task
        print("--- [1/2] Fetching Articles (RSS/NewsAPI/GNews/YouTube) ---")
        run_content_fetch()
        # print("--- [2/2] Fetching Reddit Communities ---")
        # run_reddit_fetch()
        # print("--- [Matcher] Linking Articles to Items ---")
        # match_articles_to_items()
    @app.cli.command("fetch-test")
    def fetch_test_command():
        """Runs a limited discovery run (5 queries per source) for testing."""
        from app.jobs.tasks.content.all_contents import run_content_fetch
        print("--- Starting Limited Test Run (5 queries/source) ---")
        run_content_fetch(limit=5)

    @app.cli.command("rescrape-articles")
    def rescrape_articles_command():
        """Find articles with missing content and attempt to re-scrape."""
        from app.domains.content.service.scraping import reprocess_unscraped_articles
        print("Searching for unscraped articles...")
        count = reprocess_unscraped_articles(limit=15)
        print(f"Done! Successfully recovered content for {count} articles.")

    @app.cli.command("generate-sitemap")
    def generate_sitemap_command():
        """Generate a static sitemap.xml file."""
        from app.domains.system.sitemap import generate_static_sitemap
        print("Generating sitemap...")
        count = generate_static_sitemap(app)
        print(f"Done! Sitemap generated with {count} URLs.")

    @app.cli.command("run-scheduler")
    def run_scheduler_command():
        """Run the background scheduler in a standalone process."""
        from app.jobs.scheduler import init_scheduler
        import time
        print("Starting Nexora Background Scheduler...")
        init_scheduler(app)
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            print("Scheduler stopping...")

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return f"Too many requests. Please slow down and try again later.", 429

    return app
