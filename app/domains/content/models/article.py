from app.core.extensions import db
from app.domains.relationships import article_sources

class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    body = db.Column(db.Text)
    image_url = db.Column(db.Text)

    # Sources where this article is published
    sources = db.relationship(
        "Source",
        secondary=article_sources,
        back_populates="articles"
    )
    
    # -------- Helpers --------
    @property
    def source_name(self):
        if self.sources:
            return self.sources[0].name
        return 'Unknown'
    
    @property
    def read_time_minutes(self):
        from sqlalchemy.orm.attributes import instance_state
        state = instance_state(self)
        if 'content' not in state.unloaded and self.content:
            text = self.content
        else:
            text = self.description or ""
            
        words = len(text.split())
        return max(1, words // 200)


    @property
    def preview_text(self):
        return self.description or (self.body[:160] if self.body else None)

    def __repr__(self):
        return f"<Article {self.id} '{self.title[:30]}'>"

