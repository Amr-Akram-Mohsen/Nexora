from ..models import Article
from app.core.extensions import db
from ..content_access import create_content
from sqlalchemy.exc import IntegrityError

from app.integrations.cleaner import clean_article_data
from .taxonomy import resolve_taxonomy
from ..service.command import apply_relationships

# ---------- Taxonomy ----------


def create_article(session, data):
    article = Article(
        title=data.get("title"),
        description=data.get("description"),
        body=data.get("content"),
    )

    session.add(article)
    session.flush()
    return article

def ingest_article(session, raw_data):
    cleaned = clean_article_data(raw_data)
    if not cleaned:
        return None

    try:
        section, category = resolve_taxonomy(cleaned, session)
        title_norm = cleaned.get("title", "").lower().strip()

        # 1. Deduplication by Title
        from sqlalchemy import func
        from ..models import Content
        
        article = session.query(Article).filter(func.lower(Article.title) == title_norm).first()
        
        if not article:
            article = create_article(session, cleaned)
            # 2. Wrap into Content
            content = create_content(
                session,
                obj=article,
                object_type="article",
                published_at=cleaned.get("published_at"),
                category_id=category.id,
                section_id=section.id
            )
        else:
            # Existing Article - Find its Content record
            content = session.query(Content).filter_by(
                object_type="article",
                object_id=article.id
            ).first()

        # 3. Apply relationships (including linking sources)
        if content:
            apply_relationships(content, cleaned)

        session.commit()
        return content

    except IntegrityError:
        db.session.rollback()
        return None