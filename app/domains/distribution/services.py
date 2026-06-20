# app/domains/analytics/content_generation.py
import datetime

def generate_social_post_template(asset, platform, entity_name=None, category_name=None):
    """
    Generates rule-based and template-based social media content 
    from an existing Nexora asset (Content or Item).
    """
    current_year = datetime.datetime.now().year
    entity = entity_name or getattr(asset, "title", getattr(asset, "name", "Product"))
    category = category_name or "Top Picks"
    
    # Try to determine if it's an article with linked items
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
            generated_text = f"Reel Hook: Why everyone is talking about {entity} in {current_year}.\n\n(Show quick b-roll of the item in action)\n\nCaption: Read our full review at the link in bio!"
            
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
