from app.core.extensions import db
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

def create_admin_category(name, is_active=True):
    cat = domain_create_category(name, is_active)
    db.session.commit()
    return cat

def update_admin_category(cat_id, data):
    cat = domain_update_category(cat_id, data)
    if cat:
        db.session.commit()
    return cat

def delete_admin_category(cat_id):
    cat = domain_delete_category(cat_id)
    if cat:
        db.session.commit()
    return cat

def create_admin_brand(name, industry=None, is_active=True):
    brand = domain_create_brand(name, industry, is_active)
    db.session.commit()
    return brand

def update_admin_brand(brand_id, data):
    brand = domain_update_brand(brand_id, data)
    if brand:
        db.session.commit()
    return brand

def delete_admin_brand(brand_id):
    brand = domain_delete_brand(brand_id)
    if brand:
        db.session.commit()
    return brand

def create_admin_topic(name, is_active=True):
    topic = domain_create_topic(name, is_active)
    db.session.commit()
    return topic

def update_admin_topic(topic_id, data):
    topic = domain_update_topic(topic_id, data)
    if topic:
        db.session.commit()
    return topic

def delete_admin_topic(topic_id):
    topic = domain_delete_topic(topic_id)
    if topic:
        db.session.commit()
    return topic

def update_admin_section(section_id, data):
    section = domain_update_section(section_id, data)
    if section:
        db.session.commit()
    return section

def create_admin_attribute(name, category_id=None):
    attr = domain_create_attribute(name, category_id)
    db.session.commit()
    return attr

def update_admin_attribute(attr_id, data):
    attr = domain_update_attribute(attr_id, data)
    if attr:
        db.session.commit()
    return attr

def delete_admin_attribute(attr_id):
    attr = domain_delete_attribute(attr_id)
    if attr:
        db.session.commit()
    return attr

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
