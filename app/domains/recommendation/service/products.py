from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.core.extensions import db
from app.domains.product.models import Product
from app.infrastructure import cache
@cache.memoize(timeout=3600)
def get_items_for_content(content_id: int, limit: int=8, exclude_ids: tuple | list=None, session=None) -> list[dict]:
    from app.domains.content.models import Content
    from app.domains.product.service.utils import build_item_stmt, fetch_items
    from app.domains.product.serializers import serialize_item
    from app.domains.recommendation.service.ranking import ItemScoreWeights, score_item_relevance
    from app.domains.content.service.query.utils import build_content_stmt
    session = session or db.session
    ref_stmt = build_content_stmt(active_only=False, published_only=False, eager_load='default').where(Content.id == content_id)
    reference = session.execute(ref_stmt).scalars().first()
    if not reference:
        return []
    directly_linked_ids: set[int] = {product.id for product in reference.linked_products or []}
    ref_brand_slugs = {ce.entity.slug for ce in reference.content_entities if ce.entity.entity_type == 'brand'}
    ref_brand_ids = set()
    if ref_brand_slugs:
        from app.domains.taxonomy.models import Brand
        ref_brand_ids = {b.id for b in session.query(Brand.id).filter(Brand.slug.in_(list(ref_brand_slugs))).all()}
    ref_category_id = reference.category_id
    from sqlalchemy import or_
    stmt = build_item_stmt(eager_load='card')
    if exclude_ids:
        stmt = stmt.where(Product.id.notin_(list(exclude_ids)))
    if directly_linked_ids or ref_brand_ids or ref_category_id:
        conditions = []
        if directly_linked_ids:
            conditions.append(Product.id.in_(list(directly_linked_ids)))
        if ref_brand_ids:
            conditions.append(Product.brand_id.in_(list(ref_brand_ids)))
        if ref_category_id:
            conditions.append(Product.category_id == ref_category_id)
        stmt = stmt.where(or_(*conditions))
    else:
        return []
    stmt = stmt.limit(max(limit * 4, 40))
    candidates = fetch_items(stmt, session)
    if not candidates:
        return []
    weights = ItemScoreWeights()
    scored = [(product, score_item_relevance(product, reference, weights, directly_linked_ids)) for product in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [serialize_item(product) for product, _ in scored[:limit]]
@cache.memoize(timeout=600)
def get_trending_items(limit: int=8, days: int=7, exclude_ids: tuple | list=None, session=None) -> list[dict]:
    from app.domains.product.service.utils import build_item_stmt, fetch_items
    from app.domains.product.serializers import serialize_item
    session = session or db.session
    stmt = build_item_stmt(eager_load='card').order_by((Product.view_count + Product.click_count).desc(), Product.created_at.desc())
    if exclude_ids:
        stmt = stmt.where(Product.id.notin_(list(exclude_ids)))
    if limit:
        stmt = stmt.limit(limit)
    products = fetch_items(stmt, session)
    return [serialize_item(product) for product in products]
@cache.memoize(timeout=600)
def get_popular_items_by_brand(brand_id: int, limit: int=6, session=None) -> list[dict]:
    from app.domains.product.service.utils import build_item_stmt, fetch_items
    from app.domains.product.serializers import serialize_item
    session = session or db.session
    stmt = build_item_stmt(eager_load='card').where(Product.brand_id == brand_id).order_by(Product.view_count.desc(), Product.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    products = fetch_items(stmt, session)
    return [serialize_item(product) for product in products]
@cache.memoize(timeout=3600)
def get_contents_for_item(product_id: int, limit: int=6, session=None) -> list[dict]:
    from sqlalchemy import or_
    from app.domains.content.models import Content
    from app.domains.content.service.query.utils import build_content_stmt, fetch_serialized_contents
    session = session or db.session
    ref_item = session.get(Product, product_id)
    if not ref_item:
        return []
    directly_linked = [c for c in ref_item.linked_contents or []]
    directly_linked_ids = {c.id for c in directly_linked}
    linked_results = []
    if directly_linked_ids:
        stmt = build_content_stmt(active_only=True, published_only=True, eager_load='default').where(Content.id.in_(list(directly_linked_ids))).order_by(Content.view_count.desc(), Content.published_at.desc()).limit(limit)
        linked_results = fetch_serialized_contents(stmt, session)
    if len(linked_results) >= limit:
        return linked_results[:limit]
    remaining = limit - len(linked_results)
    conditions = []
    if ref_item.brand_id and ref_item.brand:
        from app.domains.relationships import ContentEntity
        from app.domains.taxonomy.models import Entity
        entity = session.query(Entity).filter_by(slug=ref_item.brand.slug).first()
        if entity:
            conditions.append(Content.id.in_(session.query(ContentEntity.content_id).filter(ContentEntity.entity_id == entity.id).scalar_subquery()))
    if ref_item.category_id:
        conditions.append(Content.category_id == ref_item.category_id)
    if conditions:
        exclude_ids = directly_linked_ids
        stmt = build_content_stmt(active_only=True, published_only=True, eager_load='default').where(or_(*conditions)).where(Content.id.notin_(list(exclude_ids)) if exclude_ids else True).order_by(Content.view_count.desc(), Content.published_at.desc()).limit(remaining)
        supplement = fetch_serialized_contents(stmt, session)
    else:
        supplement = []
    return linked_results + supplement