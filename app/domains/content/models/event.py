from app.core.extensions import db

class Event(db.Model):
    __tablename__ = "events"
    
    id = db.Column(db.Integer, primary_key=True)
    external_uri = db.Column(db.String(255), unique=True, index=True) # NewsAPI Event URI
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text)
    event_date = db.Column(db.DateTime, index=True)
    
    # NEW — fields from Event Registry
    image_url = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(50), nullable=True)  # e.g. 'business', 'politics'
    importance = db.Column(db.Float, nullable=True)        # ER importance score (0–1)
    article_count = db.Column(db.Integer, default=0)       # ER reported article count
    last_updated = db.Column(db.DateTime, nullable=True)   # last time ER updated this event
    
    @staticmethod
    def get_or_create(external_uri, session, title=None, importance=None, image_url=None, event_type=None, summary=None, event_date=None, article_count=0, last_updated=None):
        """Get existing event or create new. Updates mutable fields on existing records."""
        if not external_uri:
            return None
        event = session.query(Event).filter_by(external_uri=external_uri).first()
        if not event:
            event = Event(
                external_uri=external_uri, 
                title=title or "Unknown Event",
                summary=summary,
                event_date=event_date,
                importance=importance,
                image_url=image_url,
                event_type=event_type,
                article_count=article_count,
                last_updated=last_updated
            )
            session.add(event)
            session.flush()
        else:
            # Update mutable fields when ER provides fresher data
            if importance is not None:
                event.importance = importance
            if image_url and not event.image_url:
                event.image_url = image_url
            if summary and not event.summary:
                event.summary = summary
            if event_date and not event.event_date:
                event.event_date = event_date
            if event_type and not event.event_type:
                event.event_type = event_type
            if article_count is not None and article_count > event.article_count:
                event.article_count = article_count
            if last_updated:
                event.last_updated = last_updated
        return event
    
    @staticmethod
    def get_by_uri(external_uri, session):
        if not external_uri:
            return None
        return session.query(Event).filter_by(external_uri=external_uri).first()
    
    articles = db.relationship("Article", back_populates="event")

