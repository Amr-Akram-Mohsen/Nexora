from app.core.extensions import db
from app.domains.system.models import Section, Category

def resolve_taxonomy(data, session=None):
    """
    Resolves section_slug and category_slug into database objects.
    Falls back to 'news' and 'uncategorized' if slugs are missing or not found.
    """
    if session is None:
        session = db.session

    section_slug = data.get("section_slug") or "news"
    category_slug = data.get("category_slug") or "uncategorized"

    section = Section.get_by_slug(section_slug, session)
    if not section:
        section = Section.get_by_slug("news", session)

    category = Category.get_by_slug(category_slug, session)
    if not category:
        category = Category.get_by_slug("uncategorized", session)

    return section, category
