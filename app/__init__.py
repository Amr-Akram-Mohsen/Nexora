# app/__init__.py
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from .models import db, User
from config import Config
from .extensions import mail, csrf, limiter, cache
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
load_dotenv()


def create_app():
    app = Flask(__name__)

    if not app.debug:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config.from_object(Config)

    db.init_app(app)

    migrate = Migrate(app, db)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

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

    from .routes import bp
    app.register_blueprint(bp)

    # ── Ensure api_models tables are created ─────────────────────
    from .api_models import LastAPIFetch, APIUsage  # noqa: F401

    # ── CLI Commands ─────────────────────────────────────────────
    @app.cli.command("seed-db")
    def seed_db_command():
        from .utils.seeder import seed_db
        seed_db()
        print("Database seeded successfully!")

    @app.cli.command("link-articles")
    def link_articles_command():
        from .utils.matcher import match_articles_to_items
        print("Starting article-to-item matcher...")
        count = match_articles_to_items()
        print(f"Matcher complete! Created {count} new links.")

    @app.cli.command("seed-noon-stores")
    def seed_noon_stores_command():
        """Seed Noon/Namshi store records for ArabClicks affiliate network."""
        from .scrapers.noon_arabclicks import seed_arabclicks_stores
        created = seed_arabclicks_stores()
        print(f"Done! {created} new ArabClicks stores seeded.")

    @app.cli.command("fetch-all")
    def fetch_all_command():
        """Runs all active fetchers in one go."""
        from .scrapers.runner import (
            run_article_fetch, run_reddit_fetch,
            run_price_refresh, run_amazon_discovery,
        )
        from .utils.matcher import match_articles_to_items
        print("--- [1/4] Fetching Articles (RSS/NewsAPI/GNews/YouTube) ---")
        run_article_fetch()
        print("--- [2/4] Fetching Reddit Communities ---")
        run_reddit_fetch()
        print("--- [3/4] Refreshing Amazon Prices ---")
        run_price_refresh()
        print("--- [4/4] Discovering Amazon Products ---")
        run_amazon_discovery()
        print("--- [Matcher] Linking Articles to Items ---")
        match_articles_to_items()
    @app.cli.command("generate-sitemap")
    def generate_sitemap_command():
        """Generate a static sitemap.xml file."""
        from .utils.sitemap_generator import generate_static_sitemap
        print("Generating sitemap...")
        count = generate_static_sitemap(app)
        print(f"Done! Sitemap generated with {count} URLs.")

    # ── CLI Commands: Scheduler ──────────────────────────────────
    @app.cli.command("run-scheduler")
    def run_scheduler_command():
        """Run the background scheduler in a standalone process."""
        from .jobs.scheduler import init_scheduler
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
