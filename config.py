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
    MAIL_SERVER        = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT          = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS       = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME      = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD      = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER= os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    ADMIN_EMAIL        = os.environ.get("ADMIN_EMAIL", "support@yoursite.com")
    MAIL_ENABLED       = True

    # ── Article / News APIs ───────────────────────────────────────
    NEWS_API_KEY    = os.environ.get("NEWS_API_KEY")
    GNEWS_API_KEY   = os.environ.get("GNEWS_API_KEY")
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

    # ── Reddit API ────────────────────────────────────────────────
    # Create an app at: https://www.reddit.com/prefs/apps  (type: "script")
    REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "None"

    # ── Amazon PA-API 5.0 ─────────────────────────────────────────
    # Requires two Amazon Associates accounts:
    #   SA → https://affiliate-program.amazon.sa
    #   AE → https://affiliate-program.amazon.ae
    # Keys come from AWS IAM, linked to your Associates account.
    AMAZON_ACCESS_KEY       = os.environ.get("AMAZON_ACCESS_KEY")
    AMAZON_SECRET_KEY       = os.environ.get("AMAZON_SECRET_KEY")
    AMAZON_ASSOCIATE_TAG_SA = os.environ.get("AMAZON_ASSOCIATE_TAG_SA", "nexora-sa-21")
    AMAZON_ASSOCIATE_TAG_AE = os.environ.get("AMAZON_ASSOCIATE_TAG_AE", "nexora-ae-21")

    # ── ArabClicks (Noon & other regional stores) ─────────────────
    # Sign up at: https://www.arabclicks.com
    ARABCLICKS_PUBLISHER_ID = os.environ.get("ARABCLICKS_PUBLISHER_ID")


# ================================================
SOCIAL_LINKS = [
  ("facebook", "https://facebook.com/Nexora"),
  ("youtube", "https://youtube.com/Nexora"),
  ("twitter", "https://twitter.com/Nexora"),
  ("instagram", "https://instagram.com/Nexora"),
  ("quora", "https://quora.com/Nexora")
]
