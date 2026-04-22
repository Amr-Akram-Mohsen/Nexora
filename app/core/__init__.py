# app/core/__init__.py
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from app.domains.user.models import User
from pathlib import Path
from app.core.extensions import db
from config import Config
from .extensions import mail, csrf, limiter, cache
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
load_dotenv()

from app.api.articles import bp as api_article_bp
from app.api.items import bp as api_item_bp
from app.api.users import bp as api_user_bp
from app.api.interactions import bp as api_interaction_bp
from app.api.stats import bp as api_dashboard_bp

from app.domains.admin import admin_bp

# from app.domains.dashboard.routes import bp as dashboard_bp

import app.domains.system

from app.domains.user.routes import bp as user_bp
from app.domains.article.routes import bp as article_bp
from app.domains.item.routes import bp as item_bp
from app.domains.interaction.routes import bp as interaction_bp
from app.domains.recommendation.routes import bp as recommendation_bp
from app.domains.system.routes import bp as system_bp



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

    db.init_app(app)

    migrate = Migrate(app, db)

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
    app.register_blueprint(article_bp)
    app.register_blueprint(item_bp)
    app.register_blueprint(interaction_bp)
    app.register_blueprint(recommendation_bp)

    app.register_blueprint(api_article_bp)
    app.register_blueprint(api_item_bp)
    app.register_blueprint(api_user_bp)
    app.register_blueprint(api_interaction_bp)
    app.register_blueprint(api_dashboard_bp)

    # app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    # ── Ensure api_models tables are created ─────────────────────
    from app.domains.external.models import LastAPIFetch, APIUsage  # noqa: F401

    @app.cli.command("seed-db")
    def seed_db_command():
        from scripts.seed import seed_db
        seed_db()
        print("Database seeded successfully!")

    @app.cli.command("link-articles")
    def link_articles_command():
        from app.domains.recommendation.matcher import match_articles_to_items
        print("Starting article-to-item matcher...")
        count = match_articles_to_items()
        print(f"Matcher complete! Created {count} new links.")

    @app.cli.command("seed-noon-stores")
    def seed_noon_stores_command():
        """Seed Noon/Namshi store records for ArabClicks affiliate network."""
        from app.integrations.ecommerce.noon import seed_arabclicks_stores
        created = seed_arabclicks_stores()
        print(f"Done! {created} new ArabClicks stores seeded.")

    @app.cli.command("fetch-all")
    def fetch_all_command():
        """Runs all active fetchers in one go."""
        from app.jobs.tasks.content.fetch_articles import (
            run_article_fetch, run_reddit_fetch
        )
        # from app.jobs.tasks.content.fetch_items import (
        #     run_price_refresh, run_amazon_discovery, run_noon_discovery, run_arabclicks_price_refresh
        # )
        from app.domains.recommendation.matcher import match_articles_to_items
        # Note: run_price_refresh and run_amazon_discovery might be in another task
        print("--- [1/2] Fetching Articles (RSS/NewsAPI/GNews/YouTube) ---")
        run_article_fetch()
        print("--- [2/2] Fetching Reddit Communities ---")
        run_reddit_fetch()
        print("--- [Matcher] Linking Articles to Items ---")
        match_articles_to_items()
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
