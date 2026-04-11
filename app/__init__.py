# app/__init__.py
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from .models import db, User
from config import Config
from .extensions import mail, csrf, limiter
from dotenv import load_dotenv
load_dotenv()

def create_app():
    app = Flask(__name__)
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
        return User.query.get(int(user_id))

    from .routes import bp
    app.register_blueprint(bp)

    # ── Ensure api_models tables are created ─────────────────────
    from .api_models import LastAPIFetch, APIUsage  # noqa: F401

    with app.app_context():
        db.create_all()

    # ── CLI Commands ─────────────────────────────────────────────
    @app.cli.command("seed-db")
    def seed_db_command():
        from .utils.seeder import seed_db
        seed_db()
        print("Database seeded successfully!")

    @app.cli.command("seed-test-data")
    def seed_test_data_command():
        from tmp.test_data_generator import generate_mock_data
        from .utils.matcher import match_articles_to_items
        print("Generating mock products and variants...")
        generate_mock_data()
        print("Mock data generation complete!")
        print("Running matcher to link items with existing articles...")
        match_articles_to_items()
        print("Done!")

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
        """Runs active fetchers in one go."""
        from .scrapers.runner import run_article_fetch, run_reddit_fetch, run_amazon_discovery, run_noon_discovery
        from .utils.matcher import match_articles_to_items
        print("--- [1/4] Fetching Articles (RSS/NewsAPI/GNews) ---")
        run_article_fetch()
        print("--- [2/4] Fetching Reddit Communities ---")
        run_reddit_fetch()
        print("--- [3/4] Discovering Amazon Products ---")
        run_amazon_discovery()
        print("--- [4/4] Discovering Noon Products (ArabClicks) ---")
        run_noon_discovery()
        print("--- [Matcher] Linking Articles to Items ---")
        match_articles_to_items()
        print("Done! All active ingestion jobs complete.")

    # ── Start background scheduler ───────────────────────────────
    from .jobs.scheduler import init_scheduler
    init_scheduler(app)

    return app
