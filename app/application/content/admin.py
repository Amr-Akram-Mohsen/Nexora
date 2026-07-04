from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.taxonomy.models import Category
from app.domains.content.service.admin import delete_admin_content_and_relations, retry_admin_pipeline, get_admin_content_inspect_raw
from app.domains.interaction.service.scoring import get_content_engagement_score
from app.domains.distribution.services import get_distribution_history
from app.domains.content.serializers import serialize_content_inspect_dto

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
        
    return {
        "content_dto": dto,
        "engagement_score": engagement_score,
        "distribution_history": distribution_history,
        "article_sources": article_sources_data
    }

from app.shared.utils.admin_helpers import execute_admin_workflow, toggle_model_flag_workflow

def delete_content_workflow(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return False
    execute_admin_workflow(delete_admin_content_and_relations, content)
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

    if action == "activate":
        for c in contents:
            c.is_active = True
    elif action == "deactivate":
        for c in contents:
            c.is_active = False
    elif action == "publish":
        for c in contents:
            c.is_published = True
    elif action == "unpublish":
        for c in contents:
            c.is_published = False
    elif action == "review":
        for c in contents:
            c.is_published = False
    elif action == "recategorize":
        if category_id is None:
            raise ValueError("Category ID is required for recategorize action")
        category = db.session.get(Category, int(category_id))
        if not category:
            raise ValueError("Target category not found")
        for c in contents:
            c.category_id = category.id
    elif action == "delete":
        for c in contents:
            delete_admin_content_and_relations(c)
    else:
        raise ValueError("Unsupported bulk action")

    db.session.commit()
    return len(contents)

def retry_pipeline_workflow(origin):
    retried = retry_admin_pipeline(origin)
    db.session.commit()
    return retried
