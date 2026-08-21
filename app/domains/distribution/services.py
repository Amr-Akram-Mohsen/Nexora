# app/domains/analytics/content_generation.py
import datetime

def generate_social_post_template(asset, platform, entity_name=None, category_name=None):
    """
    Generates rule-based and template-based social media content 
    from an existing Nexora asset (Content or Product).
    """
    current_year = datetime.datetime.now().year
    entity = entity_name or getattr(asset, "title", getattr(asset, "name", "Product"))
    category = category_name or "Top Picks"
    
    # Try to determine if it's an article with linked products
    # (Simplified rule-based check for phase 1)
    linked_items_count = 0
    if hasattr(asset, "linked_items"):
        linked_items_count = len(asset.linked_items)
        
    generated_text = ""
    post_type = "Standard Post"

    if platform == "instagram":
        if linked_items_count >= 5:
            post_type = "Instagram Carousel"
            generated_text = f"Slide 1: Top 5 {entity} you need to know about!\n\n"
            for i in range(1, 6):
                generated_text += f"Slide {i+1}: Feature highlight #{i}\n"
            generated_text += f"\nSlide 7: Read our full breakdown at the link in bio! #Nexora #{category.replace(' ', '')}"
        else:
            post_type = "Instagram Reel Concept"
            generated_text = f"Reel Hook: Why everyone is talking about {entity} in {current_year}.\n\n(Show quick b-roll of the product in action)\n\nCaption: Read our full review at the link in bio!"
            
    elif platform == "facebook":
        post_type = "Community Discussion"
        generated_text = f"Looking for a new {category}? We just reviewed the best ones for {current_year}, including {entity}. \n\nWhat is your favorite feature to look for? Let us know below! 👇\n\nRead our full guide here: [INSERT LINK]"
        
    elif platform == "youtube":
        post_type = "Video Outline"
        generated_text = f"Title Idea: I Tested Every {entity} So You Don't Have To!\n\n"
        generated_text += "0:00 - The Hook\n"
        generated_text += "1:20 - Top Features\n"
        generated_text += "4:00 - The Verdict\n\n"
        generated_text += f"Description: Check out our complete review of {entity} on Nexora: [INSERT LINK]"
        
    elif platform == "pinterest":
        post_type = "Product Pin"
        generated_text = f"Title: Ultimate {entity} Cheat Sheet\n\n"
        generated_text += f"Description: Save this quick reference guide for the best {category} in {current_year}. Essential specs and features you need to know before buying! #ShoppingGuide #{category.replace(' ', '')}"
        
    elif platform == "tiktok":
        post_type = "TikTok Script"
        generated_text = f"Hook (0-3s): Stop scrolling if you're looking for a {category}!\n\n"
        generated_text += f"Body: We just did a deep dive on {entity} and here are 3 things you need to know...\n\n"
        generated_text += "CTA: Link in bio for the full breakdown!"
        
    else:
        post_type = "Standard Share"
        generated_text = f"Check out our latest insights on {entity}: [INSERT LINK]"

    return {
        "platform": platform,
        "post_type": post_type,
        "suggested_text": generated_text
    }


def get_distribution_history(target_type: str, target_id: int) -> list[dict]:
    """Fetch and format distribution post history for a given entity."""
    from app.core.extensions import db
    from sqlalchemy import select
    from app.domains.distribution.models import DistributionPost, DistributionPlatform

    posts = db.session.execute(
        select(DistributionPost, DistributionPlatform.name)
        .join(DistributionPlatform)
        .filter(
            DistributionPost.source_target_type == target_type, 
            DistributionPost.source_target_id == target_id
        )
        .order_by(DistributionPost.created_at.desc())
    ).all()

    distribution_history = []
    for post, platform_name in posts:
        distribution_history.append({
            "platform": platform_name,
            "status": post.status,
            "publish_date": post.publish_date.strftime("%Y-%m-%d %H:%M") if post.publish_date else "-",
            "views": post.views_count,
            "likes": post.likes_count,
            "clicks": post.clicks_count
        })

    return distribution_history

def _batch_hydrate_source_titles(posts):
    from app.core.extensions import db
    from sqlalchemy import select
    from app.domains.content.models import Content
    from app.domains.product.models import Product
    
    content_ids = {p.source_target_id for p in posts if p.source_target_type == "content"}
    product_ids = {p.source_target_id for p in posts if p.source_target_type == "product"}
    titles = {}
    if content_ids:
        for cid, title in db.session.execute(select(Content.id, Content.title).where(Content.id.in_(content_ids))).all():
            titles[("content", cid)] = title or f"Content #{cid}"
    if product_ids:
        for pid, name in db.session.execute(select(Product.id, Product.name).where(Product.id.in_(product_ids))).all():
            titles[("product", pid)] = name or f"Product #{pid}"
    return titles

def get_admin_social_distribution(status_filter=None, platform_filter=None, source_type_filter=None, page=1, per_page=50):
    from app.core.extensions import db
    from sqlalchemy import select, desc
    from app.domains.distribution.models import DistributionPost, DistributionPlatform
    from app.domains.analytics.distribution_intelligence import get_social_distribution_summary
    from datetime import datetime, timezone
    
    query = (
        select(DistributionPost, DistributionPlatform.name.label("platform_name"))
        .join(DistributionPlatform)
    )
    
    if status_filter:
        query = query.where(DistributionPost.status == status_filter)
    if platform_filter:
        query = query.where(DistributionPlatform.name == platform_filter)
    if source_type_filter:
        query = query.where(DistributionPost.source_target_type == source_type_filter)
        
    query = query.order_by(desc(DistributionPost.created_at))
    
    posts_paginated = db.paginate(query, page=page, per_page=per_page, error_out=False)
    
    view_models = []
    now_utc = datetime.now(timezone.utc)
    
    platform_icons = {
        "youtube": "📺",
        "pinterest": "📌",
        "instagram": "📷",
        "facebook": "📘",
        "twitter": "🐦",
        "linkedin": "💼",
        "blog": "📝"
    }
    
    summary_stats = get_social_distribution_summary()
    titles_map = _batch_hydrate_source_titles([p[0] for p in posts_paginated.products])
    
    for post, p_name in posts_paginated.products:
        source_title = titles_map.get((post.source_target_type, post.source_target_id), f"Unknown {post.source_target_type}")
            
        is_overdue = False
        if post.status == "scheduled" and post.publish_date and post.publish_date < now_utc:
            is_overdue = True
            
        icon = platform_icons.get(p_name.lower(), "🌐")
        engagement = post.views_count + (post.likes_count * 2) + (post.shares_count * 3) + int(post.clicks_count * 1.5)
            
        view_models.append({
            "id": post.id,
            "platform": p_name,
            "platform_icon": icon,
            "source_title": source_title,
            "source_type": post.source_target_type,
            "source_id": post.source_target_id,
            "status": post.status,
            "publish_date": post.publish_date,
            "updated_at": post.updated_at,
            "is_overdue": is_overdue,
            "has_url": bool(post.external_url),
            "views": post.views_count,
            "likes": post.likes_count,
            "clicks": post.clicks_count,
            "shares": post.shares_count,
            "engagement": engagement
        })
        
    return {
        "view_models": view_models,
        "summary_stats": summary_stats,
        "pagination": posts_paginated
    }

def get_admin_scheduling_queue():
    from app.core.extensions import db
    from sqlalchemy import select
    from app.domains.distribution.models import DistributionPost, DistributionPlatform
    from datetime import datetime, timezone
    from app.domains.shared_lookups import get_platform_icon
    
    query = (
        select(DistributionPost, DistributionPlatform.name.label("platform_name"))
        .join(DistributionPlatform)
        .where(DistributionPost.status == "scheduled")
        .order_by(DistributionPost.publish_date.asc())
        .limit(10)
    )
    
    scheduled_posts = db.session.execute(query).all()
    
    view_models = []
    now_utc = datetime.now(timezone.utc)
    titles_map = _batch_hydrate_source_titles([p[0] for p in scheduled_posts])
    
    for post, platform_name in scheduled_posts:
        platform_icon = get_platform_icon(platform_name)
        is_overdue = post.publish_date and post.publish_date < now_utc
        
        view_models.append({
            "id": post.id,
            "platform": platform_name,
            "platform_icon": platform_icon,
            "source_type": post.source_target_type,
            "source_id": post.source_target_id,
            "source_title": titles_map.get((post.source_target_type, post.source_target_id), f"Unknown {post.source_target_type}"),
            "publish_date": post.publish_date,
            "is_overdue": is_overdue
        })
        
    return view_models

def generate_admin_distribution_draft(source_type, source_id, platform_name):
    from app.core.extensions import db
    from sqlalchemy import select
    from app.domains.distribution.models import DistributionPost, DistributionPlatform
    from app.domains.content.models import Content
    from app.domains.product.models import Product
    from app.domains.shared_lookups import get_source_title

    platform = db.session.execute(select(DistributionPlatform).filter_by(name=platform_name)).scalar_one_or_none()
    if not platform:
        platform = DistributionPlatform(name=platform_name)
        db.session.add(platform)
        db.session.commit()
        
    asset = None
    if source_type == "content":
        asset = db.session.get(Content, source_id)
    elif source_type == "product":
        asset = db.session.get(Product, source_id)
        
    if not asset:
        return None
        
    generated = generate_social_post_template(asset, platform_name)
    
    post = db.session.execute(
        select(DistributionPost).filter_by(
            platform_id=platform.id, 
            source_target_type=source_type, 
            source_target_id=source_id
        )
    ).scalar_one_or_none()
    
    if not post:
        post = DistributionPost(
            platform_id=platform.id,
            source_target_type=source_type,
            source_target_id=source_id,
            status="draft",
            platform_specific_text=generated["suggested_text"]
        )
        db.session.add(post)
        db.session.commit()
        
    engagement = post.views_count + (post.likes_count * 2) + (post.shares_count * 3) + int(post.clicks_count * 1.5)
    
    return {
        "post_id": post.id,
        "platform": platform_name,
        "post_type": generated["post_type"],
        "text": post.platform_specific_text,
        "status": post.status,
        "post": post,
        "engagement": engagement,
        "source_title": get_source_title(source_type, source_id)
    }

def publish_admin_distribution_post(post_id, external_url, text):
    from app.core.extensions import db
    from app.domains.distribution.models import DistributionPost
    from datetime import datetime, timezone
    
    post = db.session.get(DistributionPost, post_id)
    if not post:
        return None
        
    post.status = "published"
    post.publish_date = datetime.now(timezone.utc)
    post.external_url = external_url
    if text:
        post.platform_specific_text = text
        
    db.session.commit()
    return post
