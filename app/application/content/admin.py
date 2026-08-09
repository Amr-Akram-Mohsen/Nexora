from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.taxonomy.models import Category
from app.domains.content.service.admin.admin import retry_admin_pipeline, get_admin_content_inspect_raw
from app.domains.interaction.service.scoring import get_content_engagement_score
from app.domains.distribution.services import get_distribution_history
from app.domains.content.service.admin.serializers import serialize_content_inspect_dto
from app.domains.content.service.command import execute_bulk_content_actions, delete_content_and_relations
from app.application.content.editorial import assess_publishing_readiness

def get_content_inspect_workflow(content_id: int) -> dict:
    raw_data = get_admin_content_inspect_raw(content_id)
    if not raw_data:
        return None
    
    content = raw_data["content"]
    target = raw_data["target"]
    
    dto = serialize_content_inspect_dto(content, target)
    engagement_score = get_content_engagement_score(content_id)
    distribution_history = get_distribution_history("content", content_id)
    
    # Optional: fetch raw article_sources for the UI if needed
    article_sources_data = []
    if content.object_type == "article" and target and hasattr(target, "article_sources"):
        article_sources_data = target.article_sources
        
    extraction_assessment = None
    if dto["object_type"] == "article":
        extraction_assessment = dto.get("extraction_assessment")

    readiness = assess_publishing_readiness(dto, extraction_assessment)
        
    return {
        "content_dto": dto,
        "engagement_score": engagement_score,
        "distribution_history": distribution_history,
        "article_sources": article_sources_data,
        "publishing_readiness": readiness
    }

def get_content_rows_workflow(args, page, per_page):
    from app.domains.content.service.query.filtering import get_content_paginated
    from app.domains.content.service.admin.admin import load_admin_content_relations
    from app.domains.content.service.admin.serializers import serialize_content_row
    
    filters = args.to_dict() if hasattr(args, "to_dict") else dict(args)
    pagination, quality = get_content_paginated(
        filters=filters,
        sort_by=filters.get("sort_by", "").strip(),
        sort_dir=filters.get("sort_dir", "desc").strip(),
        page=page,
        per_page=per_page
    )
    
    targets_map, duplicate_titles = load_admin_content_relations(pagination.items, quality)
    
    serialized = [
        serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in pagination.items
    ]
    
    return serialized, pagination

from app.shared.utils.admin_helpers import execute_admin_workflow, toggle_model_flag_workflow

def delete_content_workflow(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return False
    execute_admin_workflow(delete_content_and_relations, content)
    return True

def toggle_publish_workflow(content_id, action):
    if action not in ["publish", "unpublish"]:
        raise ValueError("Invalid action parameter")
    target_value = action == "publish"
    return toggle_model_flag_workflow(Content, content_id, "is_published", target_value)

def bulk_actions_workflow(action, ids, category_id=None):
    contents = db.session.query(Content).filter(Content.id.in_(ids)).all()
    if not contents:
        return 0

    execute_bulk_content_actions(action, contents, category_id=category_id, session=db.session)
    db.session.commit()
    return len(contents)

def retry_pipeline_workflow(origin):
    retried = retry_admin_pipeline(origin)
    db.session.commit()
    return retried
