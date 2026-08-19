from sqlalchemy import select, or_, and_, func
from datetime import datetime
from app.core.extensions import db
from app.domains.user.models import User, NewsletterSubscriber
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ProductClick, RecommendationImpression, RecommendationClick
ENGAGEMENT_WEIGHTS = {'views': 1, 'clicks': 2, 'saves': 3, 'reactions': 2, 'comments': 4, 'shares': 3}

def get_user_dashboard_stats():
    role_dist = db.session.execute(select(User.is_admin, func.count(User.id)).group_by(User.is_admin)).all()
    roles = {'Admins': sum((c for is_admin, c in role_dist if is_admin)), 'Users': sum((c for is_admin, c in role_dist if not is_admin))}
    provider_dist = db.session.execute(select(User.provider, func.count(User.id)).group_by(User.provider)).all()
    providers = {p or 'local': c for p, c in provider_dist}
    growth_data = db.session.execute(select(func.to_char(User.created_at, 'YYYY-MM').label('month'), func.count(User.id)).group_by('month').order_by('month').limit(12)).all()
    growth = {m: c for m, c in growth_data if m}
    views_sub = select(View.user_id, func.count(View.id).label('cnt')).where(View.user_id.isnot(None)).group_by(View.user_id).subquery()
    clicks_sub = select(ProductClick.user_id, func.count(ProductClick.id).label('cnt')).where(ProductClick.user_id.isnot(None)).group_by(ProductClick.user_id).subquery()
    saves_sub = select(Save.user_id, func.count(Save.id).label('cnt')).group_by(Save.user_id).subquery()
    reactions_sub = select(Reaction.user_id, func.count(Reaction.id).label('cnt')).group_by(Reaction.user_id).subquery()
    comments_sub = select(Comment.user_id, func.count(Comment.id).label('cnt')).group_by(Comment.user_id).subquery()
    shares_sub = select(Share.user_id, func.count(Share.id).label('cnt')).group_by(Share.user_id).subquery()
    engagement_score_expr = func.coalesce(views_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['views'] + func.coalesce(clicks_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['clicks'] + func.coalesce(saves_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['saves'] + func.coalesce(reactions_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['reactions'] + func.coalesce(comments_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['comments'] + func.coalesce(shares_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['shares']
    stmt = select(engagement_score_expr.label('score')).select_from(User).outerjoin(views_sub, User.id == views_sub.c.user_id).outerjoin(clicks_sub, User.id == clicks_sub.c.user_id).outerjoin(saves_sub, User.id == saves_sub.c.user_id).outerjoin(reactions_sub, User.id == reactions_sub.c.user_id).outerjoin(comments_sub, User.id == comments_sub.c.user_id).outerjoin(shares_sub, User.id == shares_sub.c.user_id)
    scores = db.session.execute(stmt).scalars().all()
    from app.domains.user.service.tiers import TIER_THRESHOLDS
    tiers = {f'{TIER_THRESHOLDS[0][1]} ({TIER_THRESHOLDS[0][0]}+)': sum((1 for s in scores if s >= TIER_THRESHOLDS[0][0])), f'{TIER_THRESHOLDS[1][1]} ({TIER_THRESHOLDS[1][0]}+)': sum((1 for s in scores if TIER_THRESHOLDS[1][0] <= s < TIER_THRESHOLDS[0][0])), f'{TIER_THRESHOLDS[2][1]} ({TIER_THRESHOLDS[2][0]}+)': sum((1 for s in scores if TIER_THRESHOLDS[2][0] <= s < TIER_THRESHOLDS[1][0])), f'{TIER_THRESHOLDS[3][1]} (1-{TIER_THRESHOLDS[2][0] - 1})': sum((1 for s in scores if 0 < s < TIER_THRESHOLDS[2][0])), 'Inactive (0)': sum((1 for s in scores if s == 0))}
    return {'roles': roles, 'providers': providers, 'growth': growth, 'engagement_tiers': tiers}

def build_user_query(search, role, status, verified, subscription, provider, sort_by=None, sort_dir=None):
    views_sub = select(View.user_id, func.count(View.id).label('cnt')).where(View.user_id.isnot(None)).group_by(View.user_id).subquery()
    clicks_sub = select(ProductClick.user_id, func.count(ProductClick.id).label('cnt')).where(ProductClick.user_id.isnot(None)).group_by(ProductClick.user_id).subquery()
    saves_sub = select(Save.user_id, func.count(Save.id).label('cnt')).group_by(Save.user_id).subquery()
    reactions_sub = select(Reaction.user_id, func.count(Reaction.id).label('cnt')).group_by(Reaction.user_id).subquery()
    comments_sub = select(Comment.user_id, func.count(Comment.id).label('cnt')).group_by(Comment.user_id).subquery()
    shares_sub = select(Share.user_id, func.count(Share.id).label('cnt')).group_by(Share.user_id).subquery()
    engagement_score_expr = func.coalesce(views_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['views'] + func.coalesce(clicks_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['clicks'] + func.coalesce(saves_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['saves'] + func.coalesce(reactions_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['reactions'] + func.coalesce(comments_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['comments'] + func.coalesce(shares_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['shares']
    from sqlalchemy.orm import selectinload
    stmt = select(User, engagement_score_expr.label('engagement_score')).options(selectinload(User.newsletter_subscription)).outerjoin(views_sub, User.id == views_sub.c.user_id).outerjoin(clicks_sub, User.id == clicks_sub.c.user_id).outerjoin(saves_sub, User.id == saves_sub.c.user_id).outerjoin(reactions_sub, User.id == reactions_sub.c.user_id).outerjoin(comments_sub, User.id == comments_sub.c.user_id).outerjoin(shares_sub, User.id == shares_sub.c.user_id)
    if sort_by == 'engagement_score':
        stmt = stmt.order_by(engagement_score_expr.desc() if sort_dir == 'desc' else engagement_score_expr.asc())
    elif sort_by == 'joined':
        stmt = stmt.order_by(User.created_at.desc() if sort_dir == 'desc' else User.created_at.asc())
    elif sort_by == 'last_active':
        stmt = stmt.order_by(User.last_login_at.desc() if sort_dir == 'desc' else User.last_login_at.asc())
    else:
        stmt = stmt.order_by(User.id.desc())
    count_stmt = select(func.count(User.id))
    if search:
        search_filter = or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    if role:
        role_filter = User.is_admin == True if role.lower() == 'admin' else User.is_admin == False
        stmt = stmt.where(role_filter)
        count_stmt = count_stmt.where(role_filter)
    if status:
        status_filter = User.is_active == True if status.lower() == 'active' else User.is_active == False
        stmt = stmt.where(status_filter)
        count_stmt = count_stmt.where(status_filter)
    if verified:
        verified_filter = User.is_verified == True if verified.lower() == 'true' else User.is_verified == False
        stmt = stmt.where(verified_filter)
        count_stmt = count_stmt.where(verified_filter)
    if provider:
        provider_filter = User.provider == 'google' if provider.lower() == 'google' else User.provider.is_(None) | (User.provider == 'local')
        stmt = stmt.where(provider_filter)
        count_stmt = count_stmt.where(provider_filter)
    if subscription:
        if subscription.lower() == 'subscribed':
            sub_filter = User.newsletter_subscription.has(and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None)))
        else:
            sub_filter = ~User.newsletter_subscription.has(and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None)))
        stmt = stmt.where(sub_filter)
        count_stmt = count_stmt.where(sub_filter)
    return (stmt, count_stmt)

def get_user_analytics_metrics(id: int):
    stmt_metrics = select(select(func.count(View.id)).where(View.user_id == id).scalar_subquery(), select(func.count(ProductClick.id)).where(ProductClick.user_id == id).scalar_subquery(), select(func.count(Save.id)).where(Save.user_id == id).scalar_subquery(), select(func.count(Reaction.id)).where(Reaction.user_id == id).scalar_subquery(), select(func.count(Comment.id)).where(Comment.user_id == id).scalar_subquery(), select(func.count(Share.id)).where(Share.user_id == id).scalar_subquery())
    views_count, clicks_count, saves_count, reactions_count, comments_count, shares_count = db.session.execute(stmt_metrics).first()
    recs_seen_rows = db.session.execute(select(RecommendationImpression.entity_ids).where(RecommendationImpression.user_id == id)).scalars().all()
    recs_seen = sum((len(ids) if isinstance(ids, list) else 0 for ids in recs_seen_rows))
    recs_clicked = db.session.scalar(select(func.count(RecommendationClick.id)).where(RecommendationClick.user_id == id)) or 0
    engagement_score = views_count * ENGAGEMENT_WEIGHTS['views'] + clicks_count * ENGAGEMENT_WEIGHTS['clicks'] + saves_count * ENGAGEMENT_WEIGHTS['saves'] + reactions_count * ENGAGEMENT_WEIGHTS['reactions'] + comments_count * ENGAGEMENT_WEIGHTS['comments'] + shares_count * ENGAGEMENT_WEIGHTS['shares']
    reactions_breakdown = db.session.execute(select(Reaction.type, func.count(Reaction.id)).where(Reaction.user_id == id).group_by(Reaction.type)).all()
    likes = sum((c for t, c in reactions_breakdown if t == 'like'))
    dislikes = sum((c for t, c in reactions_breakdown if t == 'dislike'))
    sentiments = db.session.execute(select(Comment.sentiment, func.count(Comment.id)).where(Comment.user_id == id).group_by(Comment.sentiment)).all()
    pos = sum((c for s, c in sentiments if s == 'positive'))
    neu = sum((c for s, c in sentiments if s == 'neutral'))
    neg = sum((c for s, c in sentiments if s == 'negative'))
    spam = sum((c for s, c in sentiments if s == 'spam'))
    latest_comment = db.session.scalar(select(Comment).where(Comment.user_id == id).order_by(Comment.created_at.desc()).limit(1))
    latest_save = db.session.scalar(select(Save).where(Save.user_id == id).order_by(Save.created_at.desc()).limit(1))
    latest_view = db.session.scalar(select(View).where(View.user_id == id).order_by(View.created_at.desc()).limit(1))
    latest_reaction = db.session.scalar(select(Reaction).where(Reaction.user_id == id).order_by(Reaction.created_at.desc()).limit(1))
    latest_share = db.session.scalar(select(Share).where(Share.user_id == id).order_by(Share.created_at.desc()).limit(1))
    latest_click = db.session.scalar(select(ProductClick).where(ProductClick.user_id == id).order_by(ProductClick.created_at.desc()).limit(1))
    from app.domains.user.service.tiers import score_to_tier
    engagement_tier = score_to_tier(engagement_score)
    counts_dict = {'Commenter': comments_count, 'Saver': saves_count, 'Sharer': shares_count, 'Clicker': clicks_count, 'Viewer': views_count}
    max_count = max(counts_dict.values()) if any(counts_dict.values()) else 0
    engagement_profile = 'Inactive'
    if max_count > 0:
        for profile, count in counts_dict.items():
            if count == max_count:
                engagement_profile = profile
                break
    recent_activity_summary = '—'
    activities = []

    def get_title(obj):
        target = getattr(obj, 'target', None)
        return getattr(target, 'title', getattr(target, 'name', 'Unknown Product'))
    if latest_comment:
        activities.append((latest_comment.created_at, f'Commented: {latest_comment.content[:50]}...'))
    if latest_save:
        activities.append((latest_save.created_at, f'Saved: {get_title(latest_save)}'))
    if latest_view:
        activities.append((latest_view.created_at, f'Viewed: {get_title(latest_view)}'))
    if latest_reaction:
        activities.append((latest_reaction.created_at, f'Reacted ({latest_reaction.type}): {get_title(latest_reaction)}'))
    if latest_share:
        activities.append((latest_share.created_at, f'Shared: {get_title(latest_share)}'))
    if latest_click:
        activities.append((latest_click.created_at, 'Clicked Product Link'))
    if activities:
        activities.sort(key=lambda x: x[0] or datetime.min, reverse=True)
        recent_activity_summary = activities[0][1]
    return {'views_count': views_count, 'clicks_count': clicks_count, 'saves_count': saves_count, 'reactions_count': reactions_count, 'comments_count': comments_count, 'shares_count': shares_count, 'recs_seen': recs_seen, 'recs_clicked': recs_clicked, 'engagement_score': engagement_score, 'likes': likes, 'dislikes': dislikes, 'pos': pos, 'neu': neu, 'neg': neg, 'spam': spam, 'latest_comment': latest_comment, 'latest_save': latest_save, 'latest_view': latest_view, 'latest_reaction': latest_reaction, 'latest_share': latest_share, 'latest_click': latest_click, 'engagement_tier': engagement_tier, 'engagement_profile': engagement_profile, 'recent_activity_summary': recent_activity_summary}