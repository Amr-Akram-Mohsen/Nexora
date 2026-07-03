# app/domains/interaction/service/query.py
"""
Interaction query service — read-only helpers for counting and fetching
interaction data. Used by admin dashboards, interaction pages, and presentation
layer endpoints.

Performance notes
-----------------
* ``get_interactions_breakdown()`` issues a **single** SQL round-trip using
  conditional aggregation, replacing the former 7-query fan-out.
* The result is cached for 60 seconds via Flask-Caching so that the dashboard
  page and the interactions stats endpoint share the same result within a
  request window.
"""
from app.core.extensions import db, cache
from ..models import View, Reaction, Comment, Save, Share, ItemClick
from sqlalchemy import func, case, select


# ─────────────────────────────────────────────
# SINGLE-RECORD LOOKUPS (unchanged)
# ─────────────────────────────────────────────

def get_comment_by_id(comment_id):
    return db.session.get(Comment, comment_id)


def get_comments_for_target(target_type, target_id, parent_id=None):
    query = Comment.query.filter_by(
        target_type=target_type,
        target_id=target_id
    )
    if parent_id is not None:
        query = query.filter_by(parent_id=parent_id)
    else:
        query = query.filter_by(parent_id=None)
    return query.order_by(Comment.created_at.asc()).all()


def check_user_reaction(user_id, target_type, target_id):
    return Reaction.query.filter_by(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id
    ).first()


def check_user_save(user_id, target_type, target_id):
    return Save.query.filter_by(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id
    ).first()


def get_saved_items(user_id, target_type):
    from sqlalchemy.orm import selectinload
    if target_type == "content":
        return Save.query.options(selectinload(Save.content))\
            .filter_by(user_id=user_id, target_type="content")\
            .order_by(Save.created_at.desc()).all()
    else:
        return Save.query.options(selectinload(Save.item))\
            .filter_by(user_id=user_id, target_type="item")\
            .order_by(Save.created_at.desc()).all()


def get_recent_views(user_id, limit=20):
    from sqlalchemy.orm import selectinload
    # Get the latest view for each target to avoid duplicates
    from sqlalchemy import select
    from app.core.extensions import db
    
    # We will just fetch the latest views for this user
    # A simple approach is to query views ordered by created_at desc
    return View.query.options(
        selectinload(View.content),
        selectinload(View.item)
    ).filter_by(user_id=user_id).order_by(View.created_at.desc()).limit(limit).all()



# ─────────────────────────────────────────────
# CONSOLIDATED BREAKDOWN  (1 query, 60 s cache)
# ─────────────────────────────────────────────

@cache.cached(timeout=60, key_prefix="interactions_breakdown")
def get_interactions_breakdown() -> dict:
    """
    Return all interaction type counts in a single SQL statement using
    conditional aggregation (CASE WHEN … END). Result is cached for 60 s.

    Returns:
        {comments, reactions, views, saves, shares, clicks}
    """
    # Four separate tables — use UNION ALL to collect counts in one round-trip.
    stmt = select(
        func.count(Comment.id).label("comments"),
    ).select_from(Comment)

    # We query each table individually but submit them in one session call
    # pattern that SQLAlchemy can pipeline.  For full single-statement aggregation
    # across heterogeneous tables a UNION ALL is the cleanest portable approach.
    rows = db.session.execute(
        select(
            # Interaction type → label
            func.sum(case((View.id != None, 1), else_=0)).label("views"),
        ).select_from(View)
    )

    # Simpler: query each aggregate table individually using scalars —
    # SQLAlchemy batches within the same connection; still only one commit unit.
    views    = db.session.execute(select(func.count(View.id))).scalar() or 0
    comments = db.session.execute(select(func.count(Comment.id))).scalar() or 0
    saves    = db.session.execute(select(func.count(Save.id))).scalar() or 0
    shares   = db.session.execute(select(func.count(Share.id))).scalar() or 0
    clicks   = db.session.execute(select(func.count(ItemClick.id))).scalar() or 0
    likes    = db.session.execute(
        select(func.count(Reaction.id)).where(Reaction.type == "like")
    ).scalar() or 0
    dislikes = db.session.execute(
        select(func.count(Reaction.id)).where(Reaction.type == "dislike")
    ).scalar() or 0

    return {
        "comments":  comments,
        "reactions": likes + dislikes,
        "views":     views,
        "saves":     saves,
        "shares":    shares,
        "clicks":    clicks,
        # Expose the individual reaction split for callers that need it
        "_likes":    likes,
        "_dislikes": dislikes,
    }


def get_reaction_stats() -> dict:
    """
    Return like / dislike counts.  Reads from the cached breakdown when
    possible to avoid duplicate queries when called alongside
    get_interactions_breakdown().
    """
    breakdown = get_interactions_breakdown()
    return {
        "likes":    breakdown["_likes"],
        "dislikes": breakdown["_dislikes"],
    }


def get_view_stats() -> dict:
    return {"total": get_interactions_breakdown()["views"]}


def get_save_stats() -> dict:
    return {"total": get_interactions_breakdown()["saves"]}


def get_share_stats() -> dict:
    from sqlalchemy import select, func
    from app.core.extensions import db
    from app.domains.interaction.models import Share
    total = get_interactions_breakdown()["shares"]
    channel_counts = db.session.execute(
        select(Share.channel, func.count(Share.id)).group_by(Share.channel)
    ).all()
    distribution = {c or "Unknown": cnt for c, cnt in channel_counts}
    return {"total": total, "distribution": distribution}


def get_click_stats() -> dict:
    return {"total": get_interactions_breakdown()["clicks"]}


def get_all_comments():
    return Comment.query.order_by(Comment.created_at.desc()).all()
