# app/api_models.py
from app.core.extensions import db
from datetime import datetime

# ==================== LAST API FETCH ====================
class LastAPIFetch(db.Model):
    """
    Tracks the last time we fetched a specific section+query combination
    from any external API. Used to enforce cooldown periods.
    """
    __tablename__ = "last_api_fetch"

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    section      = db.Column(db.String(100), nullable=False)
    query_text   = db.Column(db.Text, nullable=False)
    last_fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "section", "query_text",
            name="unique_fetch_per_query"
        ),
    )

    def __repr__(self):
        return f"<LastAPIFetch {self.section} | {self.query_text} | {self.last_fetched_at}>"


# ==================== API USAGE ====================
class APIUsage(db.Model):
    """
    Tracks how many requests we've made to each external API per day.
    Used to stay within free-tier limits.

    api_name values: "newsapi", "gnews", "youtube", "reddit"
    """
    __tablename__ = "api_usage"

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date          = db.Column(db.Date, nullable=False)
    api_name      = db.Column(db.String(50), nullable=False, default="newsapi")
    request_count = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (
        db.UniqueConstraint(
            "date", "api_name",
            name="uq_api_usage_date_api"
        ),
    )

    def __repr__(self):
        return f"<APIUsage {self.date} | {self.api_name} | {self.request_count}>"
