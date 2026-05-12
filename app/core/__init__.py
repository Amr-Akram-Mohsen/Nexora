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

from app.admin import (
    api_user_bp, api_content_bp, api_item_bp, api_interaction_bp, api_dashboard_bp, api_ingestion_bp
)

from app.domains.user.models import User

from app.web.routes import (
    admin_bp, user_bp, system_bp, content_bp, item_bp, interaction_bp, recommendation_bp, recommendation_bp
)

class _LevelAwareFormatter(logging.Formatter):
    """Detail lines use HH:MM:SS only; ERROR/CRITICAL append source location."""
    _PLAIN  = logging.Formatter('%(asctime)s  %(levelname)-7s  %(message)s',
                                datefmt='%H:%M:%S')
    _DETAIL = logging.Formatter('%(asctime)s  %(levelname)-7s  %(message)s  [%(filename)s:%(lineno)d]',
                                datefmt='%H:%M:%S')

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            return self._DETAIL.format(record)
        return self._PLAIN.format(record)

import warnings

warnings.filterwarnings(
    "ignore",
    message="Using the in-memory storage for tracking rate limits"
)

def setup_logging(app):
    """Configure rotating file logging for production-grade audit trails."""
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # 10 MB per file, keeping last 5 backups
    file_handler = RotatingFileHandler('logs/nexora.log', maxBytes=10240000, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(_LevelAwareFormatter())
    file_handler.setLevel(logging.INFO)

    # 1. Clean up app.logger (Flask's internal logger)
    # Removing existing handlers prevents double-logging and console output in production
    app.logger.handlers = [file_handler]
    app.logger.propagate = False

    # 2. Clean up 'app' namespace logger (used by tasks and integrations)
    # This ensures all ingestion sub-loggers inherit ONLY the file handler
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    app_logger.handlers = [file_handler]
    app_logger.propagate = False

    # 3. Suppress root StreamHandlers to prevent library leakage to terminal
    # Centralize all logs in nexora.log to keep the terminal clean.
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

    # ── Register CLI Commands ────────────────────────────────────
    from .cli import register_commands
    register_commands(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return f"Too many requests. Please slow down and try again later.", 429

    return app
