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

    # ── Article / News APIs ───────────────────────────────────────
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
    GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY")
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

    # ── Reddit API ────────────────────────────────────────────────
    # Create an app at: https://www.reddit.com/prefs/apps  (type: "script")
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")

    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 days (for remember-me)

    # ── Amazon PA-API 5.0 ─────────────────────────────────────────
    # Requires two Amazon Associates accounts:
    #   SA → https://affiliate-program.amazon.sa
    #   AE → https://affiliate-program.amazon.ae
    # Keys come from AWS IAM, linked to your Associates account.
    AMAZON_ACCESS_KEY = os.environ.get("AMAZON_ACCESS_KEY")
    AMAZON_SECRET_KEY = os.environ.get("AMAZON_SECRET_KEY")
    AMAZON_ASSOCIATE_TAG_SA = os.environ.get("AMAZON_ASSOCIATE_TAG_SA", "nexora-sa-21")
    AMAZON_ASSOCIATE_TAG_AE = os.environ.get("AMAZON_ASSOCIATE_TAG_AE", "nexora-ae-21")

    # ── ArabClicks (Noon & other regional stores) ─────────────────
    # Sign up at: https://www.arabclicks.com
    ARABCLICKS_PUBLISHER_ID = os.environ.get("ARABCLICKS_PUBLISHER_ID")

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
  ("youtube", "https://youtube.com/@nexorasignals"),
  ("instagram", "https://instagram.com/nexorasignals"),
  ("x", "https://x.com/nexorasignals"),
  ("tiktok", "https://tiktok.com/@nexora.signals"),
  ("pinterest", "https://pinterest.com/nexorasignals")
]
