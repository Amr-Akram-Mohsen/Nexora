from sqlalchemy import select, func, cast
from app.core.extensions import db
from app.domains.relationships import ArticleSource
from app.domains.taxonomy.models import Source
from app.domains.content.models import Content, Article
from app.domains.external.models import LastAPIFetch
from app.domains.taxonomy.service.admin import (
    create_admin_category as domain_create_category,
    update_admin_category as domain_update_category,
    delete_admin_category as domain_delete_category,
    create_admin_brand as domain_create_brand,
    update_admin_brand as domain_update_brand,
    delete_admin_brand as domain_delete_brand,
    create_admin_topic as domain_create_topic,
    update_admin_topic as domain_update_topic,
    delete_admin_topic as domain_delete_topic,
    update_admin_section as domain_update_section,
    create_admin_attribute as domain_create_attribute,
    update_admin_attribute as domain_update_attribute,
    delete_admin_attribute as domain_delete_attribute,
)

from app.shared.utils.admin_helpers import execute_admin_workflow

def create_admin_category(name, is_active=True):
    return execute_admin_workflow(domain_create_category, name, is_active)

def update_admin_category(cat_id, data):
    return execute_admin_workflow(domain_update_category, cat_id, data)

def delete_admin_category(cat_id):
    return execute_admin_workflow(domain_delete_category, cat_id)

def create_admin_brand(name, industry=None, is_active=True):
    return execute_admin_workflow(domain_create_brand, name, industry, is_active)

def update_admin_brand(brand_id, data):
    return execute_admin_workflow(domain_update_brand, brand_id, data)

def delete_admin_brand(brand_id):
    return execute_admin_workflow(domain_delete_brand, brand_id)

def create_admin_topic(name, is_active=True):
    return execute_admin_workflow(domain_create_topic, name, is_active)

def update_admin_topic(topic_id, data):
    return execute_admin_workflow(domain_update_topic, topic_id, data)

def delete_admin_topic(topic_id):
    return execute_admin_workflow(domain_delete_topic, topic_id)

def update_admin_section(section_id, data):
    return execute_admin_workflow(domain_update_section, section_id, data)

def create_admin_attribute(name, category_id=None):
    return execute_admin_workflow(domain_create_attribute, name, category_id)

def update_admin_attribute(attr_id, data):
    return execute_admin_workflow(domain_update_attribute, attr_id, data)

def delete_admin_attribute(attr_id):
    return execute_admin_workflow(domain_delete_attribute, attr_id)

def apply_taxonomy_insight_workflow(content_id, type_, suggested_id):
    from app.domains.taxonomy.service.insights import apply_taxonomy_insight
    try:
        apply_taxonomy_insight(content_id, type_, suggested_id)
        # Assuming the domain function might not commit in the future, we ensure it's committed here.
        # It's okay if domain also commits, but ideally domain shouldn't.
        # We wrap in try/except to handle rollback appropriately for the workflow boundary.
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def get_source_inspect_workflow(id):
    from app.domains.taxonomy.service.admin import get_admin_source_inspect_raw
    from app.application.taxonomy.admin_serializers import serialize_source_inspect_dto
    
    raw_tuple = get_admin_source_inspect_raw(id)
    if not raw_tuple:
        return None
        
    dto = serialize_source_inspect_dto(raw_tuple)
    return {"source_dto": dto}

def get_category_rows_workflow(page, per_page, search, status, health):
    from app.domains.taxonomy.models import Category
    from app.domains.taxonomy.service.query import paginate_taxonomy_entity
    from app.domains.taxonomy.service.metrics import get_category_metrics
    from app.domains.taxonomy.serializers import serialize_taxonomy

    pagination = paginate_taxonomy_entity(Category, page, per_page, search, status, health)
    product_ids = [c.id for c in pagination.items]
    metrics = get_category_metrics(product_ids)
        
    serialized = []
    for c in pagination.items:
        m = metrics.get(c.id, {})
        c_count = m.get("content_count", 0)
        i_count = m.get("item_count", 0)
        
        health_status = "ok"
        if c_count == 0 and i_count == 0:
            health_status = "unused"
        elif not getattr(c, "is_active", True) and (c_count > 0 or i_count > 0):
            health_status = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "product count": i_count
        }
        serialized.append(serialize_taxonomy(c, counts=counts, health=health_status))

    return serialized, pagination

def get_brand_rows_workflow(page, per_page, search, status, health):
    from app.domains.taxonomy.models import Brand
    from app.domains.taxonomy.service.query import paginate_taxonomy_entity
    from app.domains.taxonomy.service.metrics import get_brand_metrics
    from app.domains.taxonomy.serializers import serialize_taxonomy

    pagination = paginate_taxonomy_entity(Brand, page, per_page, search, status, health)
    product_ids = [b.id for b in pagination.items]
    metrics = get_brand_metrics(product_ids)
        
    serialized = []
    for b in pagination.items:
        m = metrics.get(b.id, {})
        c_count = m.get("content_count", 0)
        i_count = m.get("item_count", 0)
        
        health_status = "ok"
        if c_count == 0 and i_count == 0:
            health_status = "unused"
        elif not getattr(b, "is_active", True) and (c_count > 0 or i_count > 0):
            health_status = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "product count": i_count,
        }
        serialized.append(serialize_taxonomy(b, counts=counts, health=health_status))

    return serialized, pagination

def get_topic_rows_workflow(page, per_page, search, status, health):
    from app.domains.taxonomy.models import Entity
    from app.domains.taxonomy.service.query import paginate_taxonomy_entity
    from app.domains.taxonomy.service.metrics import get_topic_metrics
    from app.domains.taxonomy.serializers import serialize_taxonomy

    extra_filter = Entity.entity_type.in_(['topic', 'tag', 'concept'])
    pagination = paginate_taxonomy_entity(Entity, page, per_page, search, status, health, extra_filter=extra_filter)
    product_ids = [t.id for t in pagination.items]
    metrics = get_topic_metrics(product_ids)
        
    serialized = []
    for t in pagination.items:
        m = metrics.get(t.id, {})
        c_count = m.get("content_count", 0)
        cat_count = m.get("category_spread", 0)
        
        health_status = "ok"
        if c_count == 0:
            health_status = "unused"
        elif not getattr(t, "is_active", True) and c_count > 0:
            health_status = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "category spread": cat_count
        }
        serialized.append(serialize_taxonomy(t, counts=counts, health=health_status))

    return serialized, pagination

def get_section_rows_workflow(page, per_page, search, status, health):
    from app.domains.taxonomy.models import Section
    from app.domains.taxonomy.service.query import paginate_taxonomy_entity
    from app.domains.taxonomy.service.metrics import get_section_metrics
    from app.domains.taxonomy.serializers import serialize_taxonomy

    pagination = paginate_taxonomy_entity(Section, page, per_page, search, status, health)
    product_ids = [s.id for s in pagination.items]
    metrics = get_section_metrics(product_ids)
        
    serialized = []
    for s in pagination.items:
        m = metrics.get(s.id, {})
        c_count = m.get("content_count", 0)
        cat_count = m.get("category_spread", 0)
        
        health_status = "ok"
        if c_count == 0:
            health_status = "unused"
        elif not getattr(s, "is_active", True) and c_count > 0:
            health_status = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "category count": cat_count
        }
        serialized.append(serialize_taxonomy(s, counts=counts, health=health_status))

    return serialized, pagination

def get_attribute_rows_workflow(page, per_page, search, health):
    from app.domains.taxonomy.models import AttributeFacet
    from app.domains.taxonomy.service.query import paginate_taxonomy_entity
    from app.domains.taxonomy.service.metrics import get_attribute_metrics

    pagination = paginate_taxonomy_entity(AttributeFacet, page, per_page, search, health=health)
    product_ids = [a.id for a in pagination.items]
    metrics = get_attribute_metrics(product_ids)
        
    serialized = []
    for a in pagination.items:
        m = metrics.get(a.id, {})
        c_count = m.get("content_count", 0)
        
        health_status = "ok"
        if c_count == 0:
            health_status = "unused"
            
        data = {
            "id": a.id,
            "name": a.name,
            "category": a.category.name if a.category else "Global",
            "content count": str(c_count),
            "health": health_status
        }
        serialized.append(data)

    return serialized, pagination

def get_facet_rows_workflow(model, field_id_name, page, per_page, search, health):
    from app.domains.taxonomy.service.query import paginate_taxonomy_entity
    from app.domains.taxonomy.service.metrics import get_facet_metrics

    pagination = paginate_taxonomy_entity(model, page, per_page, search, health=health, field_name=field_id_name)
    product_ids = [a.id for a in pagination.items]
    metrics = get_facet_metrics(product_ids, field_id_name)
    
    serialized = []
    for a in pagination.items:
        m = metrics.get(a.id, {})
        c_count = m.get("content_count", 0)
        
        h_status = "ok"
        if c_count == 0:
            h_status = "unused"
            
        data = {
            "id": a.id,
            "name": a.name,
            "content count": str(c_count),
            "health": h_status
        }
        serialized.append(data)

    return serialized, pagination

