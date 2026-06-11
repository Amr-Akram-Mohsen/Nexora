# app/core/__init__.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, render_template
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from pathlib import Path
from config import Config
from .extensions import mail, csrf, limiter, cache, migrate, db
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from logging.handlers import RotatingFileHandler
import os
import warnings


# Register every ORM model before admin/routes import eager-load or mapper setup.
from app import domains  # noqa: F401

from app.admin import (
    api_user_bp,
    api_content_bp,
    api_item_bp,
    api_interaction_bp,
    api_dashboard_bp,
    api_ingestion_bp,
    api_system_bp,
    api_taxonomy_bp,
    api_recommendation_bp,
)

from app.domains.user.models import User

from app.web.routes import (
    admin_bp,
    user_bp,
    system_bp,
    content_bp,
    item_bp,
    interaction_bp,
    recommendation_bp,
)

load_dotenv()


class _LevelAwareFormatter(logging.Formatter):
    """Detail lines use HH:MM:SS only; ERROR/CRITICAL append source location."""

    _PLAIN = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S"
    )
    _DETAIL = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s  [%(filename)s:%(lineno)d]",
        datefmt="%H:%M:%S",
    )

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            return self._DETAIL.format(record)
        return self._PLAIN.format(record)


warnings.filterwarnings(
    "ignore", message="Using the in-memory storage for tracking rate limits"
)


def setup_logging(app):
    """Configure domain-specific rotating file logging."""
    if not os.path.exists("logs"):
        os.mkdir("logs")

    # Shared formatter
    formatter = _LevelAwareFormatter()
    log_cfg = {"maxBytes": 10240000, "backupCount": 5, "encoding": "utf-8"}

    # 1. Ingestion & Discovery log
    class IngestionFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return "[FETCH]" in msg or ("[INGEST]" in msg and "[rescrape]" not in msg) or "[DISCOVERY]" in msg or "[BATCH]" in msg

    ingest_h = RotatingFileHandler("logs/ingestion.log", **log_cfg)
    ingest_h.setFormatter(formatter)
    ingest_h.setLevel(logging.INFO)
    ingest_h.addFilter(IngestionFilter())

    # 2. Enrichment (Scraping) log
    class EnrichmentFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return "[SCRAPE]" in msg or "[rescrape]" in msg

    enrich_h = RotatingFileHandler("logs/enrichment.log", **log_cfg)
    enrich_h.setFormatter(formatter)
    enrich_h.setLevel(logging.INFO)
    enrich_h.addFilter(EnrichmentFilter())

    # 3. Web Routes log
    class RouteFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return "[ROUTE]" in msg or "[AUTH]" in msg

    route_h = RotatingFileHandler("logs/routes.log", **log_cfg)
    route_h.setFormatter(formatter)
    route_h.setLevel(logging.INFO)
    route_h.addFilter(RouteFilter())

    # 4. Auth log
    class AuthFilter(logging.Filter):
        def filter(self, record):
            return "[AUTH]" in record.getMessage()

    auth_h = RotatingFileHandler("logs/auth.log", **log_cfg)
    auth_h.setFormatter(formatter)
    auth_h.setLevel(logging.INFO)
    auth_h.addFilter(AuthFilter())

    # Apply handlers to the 'app' logger (where our custom logs go)
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.handlers = [ingest_h, enrich_h, route_h, auth_h]
    app_logger.propagate = False

    # Apply route handler to Flask's logger (for request logs)
    app.logger.handlers = [route_h]
    app.logger.propagate = False

    # Root logger handles library warnings only
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    for h in root_logger.handlers[:]:
        if type(h) is logging.StreamHandler:
            root_logger.removeHandler(h)


def create_app():
    base_dir = Path(__file__).resolve().parent  # app/core

    app = Flask(
        __name__,
        template_folder=str(base_dir.parent / "web" / "templates"),
        static_folder=str(base_dir.parent / "web" / "static"),
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
    login_manager.login_view = "user.login"

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
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
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
    app.register_blueprint(api_system_bp)
    app.register_blueprint(api_taxonomy_bp)
    app.register_blueprint(api_recommendation_bp)

    # app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def check_maintenance():
        # Exclude admin routes, static files, and login/logout endpoints
        if (request.path.startswith("/admin") or 
            request.path.startswith("/static") or 
            "login" in request.path or 
            "logout" in request.path):
            return
            
        # Allow logged in admins to bypass maintenance mode
        from flask_login import current_user
        if current_user.is_authenticated and getattr(current_user, "is_admin", False):
            return

        lock_file = os.path.join(app.instance_path, "maintenance.lock")
        if os.path.exists(lock_file):
            return render_template("maintenance.html"), 503

    # ── Register CLI Commands ────────────────────────────────────
    from .cli import register_commands

    register_commands(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return "Too many requests. Please slow down and try again later.", 429

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    return app
