def unlink_match_workflow(content_id, product_id):
    from app.domains.recommendation.service.admin.command import delete_match
    return delete_match(content_id, product_id)
def get_match_inspect_workflow(content_id: int):
    from app.domains.recommendation.service.admin.admin import get_admin_match_inspect_raw
    from app.domains.recommendation.service.admin.serializers import serialize_match_inspect_dto
    raw_tuple = get_admin_match_inspect_raw(content_id)
    if not raw_tuple:
        return None
    dto = serialize_match_inspect_dto(raw_tuple)
    return {'match_dto': dto}
def get_user_interests_workflow(user_id: int):
    from app.domains.recommendation.service.admin.admin import get_admin_user_interests_raw
    from app.domains.recommendation.service.admin.serializers import serialize_user_interests_dto
    raw_tuple = get_admin_user_interests_raw(user_id)
    if not raw_tuple:
        return None
    dto = serialize_user_interests_dto(raw_tuple)
    return {'user_interests_dto': dto}