from datetime import datetime
from app.core.extensions import db
from app.domains.recommendation.models import UserInterest, UserEntityInterest
from app.domains.product.models import Product
from app.domains.content.models import Article
from app.shared.constants.core import TargetType
from sqlalchemy import select

INTEREST_WEIGHTS = {
    'view': 0,
    'product_click': 0.5,
    'like': 1.0,
    'dislike': -0.7,
    'comment': 0.4,
    'comment_positive': 1.2,
    'comment_negative': -1.0,
}

def extract_entities_from_target(target):
    if isinstance(target, Product):
        return [{'brand_id': target.brand_id, 'category_id': target.category_id}]
    if isinstance(target, Article):
        entities = []
        for topic in target.topics:
            entities.append({'topic_id': topic.id})
        entities.append({'category_id': target.category_id})
        for brand in target.brands:
            entities.append({'brand_id': brand.id})
        return entities
    return []

def update_user_interest(*, user_id, target_type, target_id, action, increment_interaction=False, entities=None, session=None):
    session = session or db.session
    entities = entities or {}
    weight = INTEREST_WEIGHTS.get(action)
    stmt_interest = select(UserInterest).where(UserInterest.user_id == user_id, UserInterest.target_type == target_type, UserInterest.target_id == target_id)
    user_interest = session.execute(stmt_interest).scalars().first()
    if not user_interest:
        user_interest = UserInterest(user_id=user_id, target_type=target_type, target_id=target_id, interaction_count=0, last_interaction_at=datetime.utcnow())
        session.add(user_interest)
        session.flush()
    if increment_interaction:
        user_interest.interaction_count += 1
        user_interest.last_interaction_at = datetime.utcnow()
    if weight is not None and entities:
        stmt_entity = select(UserEntityInterest).filter_by(user_interest_id=user_interest.id, **entities)
        entity_interest = session.execute(stmt_entity).scalars().first()
        if entity_interest:
            entity_interest.score += weight
        else:
            session.add(UserEntityInterest(user_interest_id=user_interest.id, score=weight, **entities))

def handle_interaction_interest(user, target, action, session=None):
    if not user or not target:
        return
    target_type = TargetType.PRODUCT if isinstance(target, Product) else TargetType.ARTICLE
    update_user_interest(user_id=user.id, target_type=target_type, target_id=target.id, action=action, increment_interaction=True, session=session)
    for entity in extract_entities_from_target(target):
        update_user_interest(user_id=user.id, target_type=target_type, target_id=target.id, action=action, entities=entity, session=session)

def handle_comment_interaction(user, target, comment_sentiment, session=None):
    if not user or not target:
        return
    sentiment_action = {'positive': 'comment_positive', 'negative': 'comment_negative'}.get(comment_sentiment)
    if not sentiment_action:
        return
    target_type = TargetType.PRODUCT if isinstance(target, Product) else TargetType.ARTICLE
    for entity in extract_entities_from_target(target):
        update_user_interest(user_id=user.id, target_type=target_type, target_id=target.id, action=sentiment_action, entities=entity, session=session)