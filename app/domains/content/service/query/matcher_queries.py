from app.core.extensions import db
from app.domains.content.models import Article, Content
from datetime import datetime

def get_unmatched_articles_query(cutoff: datetime, since: datetime = None, session=None):
    """
    Returns a query for unmatched (or stale matched) articles.
    """
    if session is None:
        session = db.session
        
    article_q = (
        session.query(Article)
        .join(Content, (Content.object_type == "article") & (Content.object_id == Article.id))
        .filter(
            db.or_(
                Article.last_matched_at.is_(None),
                Article.last_matched_at < cutoff,
            )
        )
    )
    if since:
        article_q = article_q.filter(Content.published_at >= since)
        
    return article_q
