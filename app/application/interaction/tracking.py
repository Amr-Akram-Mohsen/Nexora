import logging
from app.core.extensions import db
from app.domains.interaction.service import record_view
from app.domains.interaction.service.tracking import track_recommendation_impression, track_recommendation_click

logger = logging.getLogger(__name__)

def track_view_workflow(target_id: int, target_type, user, ip: str) -> dict:
    result = record_view(target_id, target_type, user, ip)
    db.session.commit()
    return result

def _execute_tracking(operation, *args, **kwargs) -> bool:
    success = operation(*args, **kwargs)
    if success:
        db.session.commit()
    else:
        db.session.rollback()
    return success

def track_impression_workflow(entity_type: str, entity_ids: list, context_id: str, user_id: int) -> bool:
    return _execute_tracking(track_recommendation_impression, entity_type, entity_ids, context_id, user_id)

def track_click_workflow(entity_type: str, entity_id: int, context_id: str, user_id: int) -> bool:
    return _execute_tracking(track_recommendation_click, entity_type, entity_id, context_id, user_id)
