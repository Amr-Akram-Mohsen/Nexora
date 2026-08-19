# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "nexora.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # ── Mail ─────────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER= os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "support@yoursite.com")
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "False").lower() == "true"

    HF_API_URL = os.environ.get("HF_API_URL")
    HF_TOKEN = os.environ.get("HF_TOKEN")

    # ── Article / News APIs ───────────────────────────────────────
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    NEWSAPI_AI_API_KEY = os.environ.get("NEWSAPI_AI_API_KEY")
    DIFFBOT_API_KEY = os.environ.get("DIFFBOT_API_KEY")

    FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
    JINA_AI_API_KEY = os.environ.get("JINA_AI_API_KEY")


    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 days
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30    # 30 days


    # ── Cache Configuration ───────────────────────────────────────
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 3600))

    # ── Engagement Scoring Weights ─────────────────────────────────
    ENGAGEMENT_WEIGHT_VIEW = float(os.environ.get("ENGAGEMENT_WEIGHT_VIEW", 1.0))
    ENGAGEMENT_WEIGHT_LIKE = float(os.environ.get("ENGAGEMENT_WEIGHT_LIKE", 3.0))
    ENGAGEMENT_WEIGHT_COMMENT = float(os.environ.get("ENGAGEMENT_WEIGHT_COMMENT", 5.0))
    ENGAGEMENT_WEIGHT_SAVE = float(os.environ.get("ENGAGEMENT_WEIGHT_SAVE", 4.0))
    ENGAGEMENT_WEIGHT_SHARE = float(os.environ.get("ENGAGEMENT_WEIGHT_SHARE", 6.0))
    ENGAGEMENT_WEIGHT_CLICK = float(os.environ.get("ENGAGEMENT_WEIGHT_CLICK", 5.0))

# ================================================
SOCIAL_LINKS = [
  ("facebook", "https://www.facebook.com/profile.php?id=61590735370977"),
  ("instagram", "https://instagram.com/nexorasignals"),
  ("pinterest", "https://pinterest.com/nexorasignals"),
  ("youtube", "https://youtube.com/@nexorasignals"),
  ("tiktok", "https://tiktok.com/@nexora.signals"),
  ("x", "https://x.com/nexorasignals")
]
