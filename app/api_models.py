from app.models import db
# ==================== LAST API FETCH ====================
class LastAPIFetch(db.Model):
    __tablename__ = "last_api_fetch"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    section = db.Column(db.String(100), nullable=False)
    query_text = db.Column(db.Text, nullable=False)

    last_fetched_at = db.Column(db.DateTime, nullable=False)
    # last_fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
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
    __tablename__ = "api_usage"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    request_count = db.Column(db.Integer, nullable=False, default=1)
    # request_count = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<APIUsage {self.date} | {self.request_count}>"
