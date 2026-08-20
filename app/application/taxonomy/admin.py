from app.core.extensions import db
from app.domains.taxonomy.service.admin.admin import (
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
    get_source_inspect_data,
    get_category_rows_data,
    get_brand_rows_data,
    get_topic_rows_data,
    get_section_rows_data,
    get_attribute_rows_data,
    get_facet_rows_data,
)
from app.domains.taxonomy.service.admin.insights import apply_taxonomy_insight
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
    try:
        apply_taxonomy_insight(content_id, type_, suggested_id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def get_source_inspect_workflow(id):
    return get_source_inspect_data(id)

def get_category_rows_workflow(page, per_page, search, status, health):
    return get_category_rows_data(page, per_page, search, status, health)

def get_brand_rows_workflow(page, per_page, search, status, health):
    return get_brand_rows_data(page, per_page, search, status, health)

def get_topic_rows_workflow(page, per_page, search, status, health):
    return get_topic_rows_data(page, per_page, search, status, health)

def get_section_rows_workflow(page, per_page, search, status, health):
    return get_section_rows_data(page, per_page, search, status, health)

def get_attribute_rows_workflow(page, per_page, search, health):
    return get_attribute_rows_data(page, per_page, search, health)

def get_facet_rows_workflow(model, field_id_name, page, per_page, search, health):
    return get_facet_rows_data(model, field_id_name, page, per_page, search, health)