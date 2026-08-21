"""
Admin Taxonomy Application Workflows.

Contains orchestrations that cross domain boundaries (e.g., merging entities
and updating associations across Content, Products, and Taxonomy).
"""
from app.core.extensions import db
from app.domains.taxonomy.service.admin.duplicates import merge_taxonomy_entities
from app.domains.taxonomy.service.admin.insights import apply_taxonomy_insight

def merge_taxonomy_entities_workflow(domain: str, source_id: int, target_id: int):
    """
    Cross-domain workflow: Merges duplicate taxonomy entities and re-links
    associated contents, products, and facets.
    """
    try:
        merge_taxonomy_entities(domain, source_id, target_id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def apply_taxonomy_insight_workflow(content_id: int, type_: str, suggested_id: int):
    """
    Cross-domain workflow: Applies a taxonomy classification insight to a content item.
    """
    try:
        apply_taxonomy_insight(content_id, type_, suggested_id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e