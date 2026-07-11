from app.core.extensions import db

class Event(db.Model):
    __tablename__ = "events"
    
    id = db.Column(db.Integer, primary_key=True)
    external_uri = db.Column(db.String(255), unique=True, index=True) # NewsAPI Event URI
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text)
    event_date = db.Column(db.DateTime, index=True)
    
    @staticmethod
    def get_or_create(external_uri, session, title=None):
        if not external_uri:
            return None
        event = session.query(Event).filter_by(external_uri=external_uri).first()
        if not event:
            event = Event(
                external_uri=external_uri, 
                title=title or "Unknown Event"
            )
            session.add(event)
            session.flush()
        return event
    
    articles = db.relationship("Article", back_populates="event")
