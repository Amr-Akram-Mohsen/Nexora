from ..models import Article
from app.core.extensions import db
from ..content_access import create_content
from sqlalchemy.exc import IntegrityError

from app.integrations.cleaner import clean_article_data
from app.domains.system.models import Section, Category
from ..service.command import apply_relationships

# ---------- Taxonomy ----------
def resolve_taxonomy(data):
    section = Section.get_by_slug(data.get("section_slug") or "news", db.session)
    if not section:
        section = Section.get_by_slug("news", db.session)

    category = Category.get_by_slug(data.get("category_slug") or "uncategorized", db.session)
    if not category:
        category = Category.get_by_slug("uncategorized", db.session)

    return section, category


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
        section, category = resolve_taxonomy(cleaned)

        article = create_article(session, cleaned)

        # 🔹 2. Wrap into Content
        content = create_content(
            db.session,
            obj=article,
            object_type="article",
            published_at=cleaned.get("published_at"),
            category_id=category.id,
            section_id=section.id
        )

        # 3. Apply relationships
        apply_relationships(content, cleaned)

        session.commit()
        return content

    except IntegrityError:
        db.session.rollback()
        return None