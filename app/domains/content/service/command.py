from app.core.extensions import db
from ..models import Article, Content
from ...system.models import (
    Topic, Brand, AttributeFacet,
    GenderFacet, IntentFacet, PriceTierFacet, Source
)
from app.shared.utils.slug import generate_slug
from .content_access import resolve
from sqlalchemy import func, insert
from sqlalchemy.orm import joinedload

def link_article_sources(article, data):
    """Links an article to its specific source URL, ensuring uniqueness."""
    source_name = data.get("source_name")
    url = data.get("url")

    if not source_name or not url:
        return

    slug = generate_slug(source_name)
    source = Source.get_by_slug(slug, db.session)

    if not source:
        return

    from ...relationships import article_sources
    
    # 🔹 Check if this specific URL is already in the system (unique constraint)
    existing_url = db.session.query(article_sources).filter_by(url=url).first()
    if existing_url:
        return

    # 🔹 Check if the link already exists for this article/source pair
    existing_link = db.session.query(article_sources).options(joinedload(Source)).filter_by(
        article_id=article.id,
        source_id=source.id
    ).first()

    if not existing_link:
        db.session.execute(
            insert(article_sources).values(
                article_id=article.id,
                source_id=source.id,
                url=url
            )
        )

def delete_content(id: int) -> bool:
    content = db.session.get(Article, id)

    if not content:
        return False

    db.session.delete(content)
    db.session.commit()
    return True

def create_content_entry(session, obj, object_type, published_at):
    """
    Creates a Content entry after the object is created.
    Prevents duplicates.
    """

    existing = session.query(Content).filter_by(
        object_type=object_type,
        object_id=obj.id
    ).first()

    if existing:
        return existing

    content = Content(
        object_type=object_type,
        object_id=obj.id,
        published_at=published_at
    )

    session.add(content)
    return content

def apply_relationships(content, data):

    # -------- Topics --------
    for slug in data.get("topic_slugs", []):
        topic = Topic.get_by_slug(slug, db.session)
        if topic:
            content.add_topic(topic)

    # -------- Brands --------
    for slug in data.get("brand_slugs", []):
        brand = Brand.get_by_slug(slug, db.session)
        if brand:
            content.add_brand(brand)

    # -------- Attributes --------
    for slug in data.get("facets", {}).get("attributes", []):
        attr = AttributeFacet.get_by_slug(slug, db.session)
        if attr:
            content.add_attribute(attr)

    # -------- Facets --------
    facets = data.get("facets", {})

    if facets.get("gender"):
        g = GenderFacet.get_by_slug(facets["gender"], db.session)
        if g:
            content.gender_id = g.id

    if facets.get("intent"):
        i = IntentFacet.get_by_slug(facets["intent"], db.session)
        if i:
            content.intent_id = i.id

    if facets.get("price_tier"):
        p = PriceTierFacet.get_by_slug(facets["price_tier"], db.session)
        if p:
            content.price_tier_id = p.id

    # -------- Sources (ONLY for article) --------
    if content.object_type == "article":
        obj = resolve(content, db.session)
        if obj:
            link_article_sources(obj, data)
