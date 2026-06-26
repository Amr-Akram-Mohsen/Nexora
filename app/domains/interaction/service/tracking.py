from app.core.extensions import db
from app.domains.interaction.models import RecommendationImpression, RecommendationClick
import logging

logger = logging.getLogger(__name__)

def track_recommendation_impression(entity_type: str, entity_ids: list, context_id: str = None, user_id: int = None) -> bool:
    try:
        impression = RecommendationImpression(
            entity_type=entity_type,
            context_id=str(context_id) if context_id is not None else None,
            entity_ids=entity_ids,
            user_id=user_id
        )
        db.session.add(impression)
        return True
    except Exception as e:
        logger.exception("Failed to track recommendation impression")
        return False

def track_recommendation_click(entity_type: str, entity_id: str, context_id: str = None, user_id: int = None) -> bool:
    try:
        click = RecommendationClick(
            entity_type=entity_type,
            entity_id=str(entity_id),
            context_id=str(context_id) if context_id is not None else None,
            user_id=user_id
        )
        db.session.add(click)
        return True
    except Exception as e:
        logger.exception("Failed to track recommendation click")
        return False
