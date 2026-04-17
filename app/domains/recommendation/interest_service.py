from datetime import datetime
from app.core.extensions import db
from .models import UserInterest, UserEntityInterest
from app.domains.item.models import Item
from app.domains.article.models import Article
from .interest_weights import INTEREST_WEIGHTS
from app.core.constants import TargetType

def extract_entities_from_target(target):
    if isinstance(target, Item):
        return [{
            "brand_id": target.brand_id,
            "category_id": target.category_id
        }]

    if isinstance(target, Article):
        entities = []

        for topic in target.topics:
            entities.append({"topic_id": topic.id})

        entities.append({"category_id": target.category_id})

        for brand in target.brands:
            entities.append({"brand_id": brand.id})

        return entities

    return []

def update_user_interest(
    *,
    user_id,
    target_type,
    target_id,
    action,
    increment_interaction=False,
    entities=None
):
    entities = entities or {}
    weight = INTEREST_WEIGHTS.get(action)

    user_interest = UserInterest.query.filter_by(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id
    ).first()

    if not user_interest:
        user_interest = UserInterest(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            interaction_count=0,
            last_interaction_at=datetime.utcnow()
        )
        db.session.add(user_interest)
        db.session.flush()

    if increment_interaction:
        user_interest.interaction_count += 1
        user_interest.last_interaction_at = datetime.utcnow()

    if weight is not None and entities:
        entity_interest = UserEntityInterest.query.filter_by(
            user_interest_id=user_interest.id,
            **entities
        ).first()

        if entity_interest:
            entity_interest.score += weight
        else:
            db.session.add(
                UserEntityInterest(
                    user_interest_id=user_interest.id,
                    score=weight,
                    **entities
                )
            )

def handle_interaction_interest(user, target, action):
    if not user or not target:
        return

    target_type = (
        TargetType.ITEM if isinstance(target, Item)
        else TargetType.ARTICLE
    )

    # 1️⃣ Always increment interaction for the target itself
    update_user_interest(
        user_id=user.id,
        target_type=target_type,
        target_id=target.id,
        action=action,
        increment_interaction=True
    )

    # 2️⃣ Entity-level scoring
    for entity in extract_entities_from_target(target):
        update_user_interest(
            user_id=user.id,
            target_type=target_type,
            target_id=target.id,
            action=action,
            entities=entity
        )
    
def handle_comment_interaction(user, target, comment_sentiment):
    if not user or not target:
        return

    sentiment_action = {
        "positive": "comment_positive",
        "negative": "comment_negative"
    }.get(comment_sentiment)

    if not sentiment_action:
        return

    # sentiment influence (NO interaction increment)
    target_type = TargetType.ITEM if isinstance(target, Item) else TargetType.ARTICLE

    for entity in extract_entities_from_target(target):
        update_user_interest(
            user_id=user.id,
            target_type=target_type,
            target_id=target.id,
            action=sentiment_action,
            entities=entity
        )
    

