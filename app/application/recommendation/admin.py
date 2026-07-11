from app.core.extensions import db
from app.domains.relationships import content_products

def unlink_match_workflow(content_id, product_id):
    db.session.execute(
        content_products.delete().where(
            content_products.c.content_id == content_id,
            content_products.c.product_id == product_id,
        )
    )
    db.session.commit()
    return True

def get_match_inspect_workflow(content_id: int):
    from app.domains.recommendation.service.admin import get_admin_match_inspect_raw
    from app.domains.recommendation.serializers import serialize_match_inspect_dto
    
    raw_tuple = get_admin_match_inspect_raw(content_id)
    if not raw_tuple:
        return None
        
    dto = serialize_match_inspect_dto(raw_tuple)
    return {"match_dto": dto}

def get_user_interests_workflow(user_id: int):
    from app.domains.recommendation.service.admin import get_admin_user_interests_raw
    from app.domains.recommendation.serializers import serialize_user_interests_dto
    
    raw_tuple = get_admin_user_interests_raw(user_id)
    if not raw_tuple:
        return None
        
    dto = serialize_user_interests_dto(raw_tuple)
    return {"user_interests_dto": dto}
