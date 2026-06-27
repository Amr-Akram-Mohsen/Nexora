from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.taxonomy.models import Category
from app.domains.content.service.admin import delete_admin_content_and_relations, retry_admin_pipeline

def delete_content_workflow(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return False
    delete_admin_content_and_relations(content)
    db.session.commit()
    return True

def toggle_publish_workflow(content_id, action):
    content = db.session.get(Content, content_id)
    if not content:
        return None
    
    if action == "publish":
        content.is_published = True
    elif action == "unpublish":
        content.is_published = False
    else:
        raise ValueError("Invalid action parameter")

    db.session.commit()
    return content

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
