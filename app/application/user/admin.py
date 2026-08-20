from app.domains.user.service import deactivate_user as domain_deactivate_user, activate_user as domain_activate_user
from app.domains.user.service.admin.admin import toggle_admin_user as domain_toggle_admin_user, get_admin_user_inspect_raw
from app.domains.user.service.admin.analytics import get_user_analytics_metrics
from app.domains.user.serializers import serialize_user_inspect_dto
from app.shared.utils.admin_helpers import execute_admin_workflow, delete_model_workflow


def get_user_inspect_workflow(user_id: int) -> dict:
    user = get_admin_user_inspect_raw(user_id)
    if not user:
        return None
    metrics = get_user_analytics_metrics(user_id)
    from app.domains.user.service.admin.admin import build_user_inspect_maps
    brands_map, categories_map, topics_map, items_map, articles_map = build_user_inspect_maps(user)
    dto = serialize_user_inspect_dto(user, metrics, brands_map, categories_map, topics_map, items_map, articles_map)
    return {'user_dto': dto}


def deactivate_user_workflow(user_id):
    return execute_admin_workflow(domain_deactivate_user, user_id)


def activate_user_workflow(user_id):
    return execute_admin_workflow(domain_activate_user, user_id)


def toggle_admin_user_workflow(user_id):
    return execute_admin_workflow(domain_toggle_admin_user, user_id)


def delete_subscriber_workflow(sub_id):
    from app.domains.user.models import NewsletterSubscriber
    return delete_model_workflow(NewsletterSubscriber, sub_id)