# app/domains/interaction/service/insights/asset_mapping.py
from sqlalchemy import select
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.taxonomy.models import Category, Brand

def map_content_strategy_to_assets(content_strategy_data):
    """
    Maps content strategy suggestions to existing database assets (Articles, Videos, Product pages)
    and identifies missing content gaps.
    """
    # Query database assets
    content_rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.category_id, Content.intent_id)
    ).all()
    
    item_rows = db.session.execute(
        select(Item.id, Item.name, Item.category_id, Item.brand_id)
    ).all()

    categories = db.session.execute(select(Category.id, Category.name)).all()
    cat_id_to_name = {c[0]: c[1] for c in categories}
    
    brands = db.session.execute(select(Brand.id, Brand.name)).all()
    brand_id_to_name = {b[0]: b[1] for b in brands}

    STOPWORDS = {"a", "an", "the", "and", "or", "of", "in", "to", "for", "is", "on", "with", "it", "at", "by", "from", "how", "ultimate", "complete", "best", "top", "guide", "cheat", "sheet", "checklist", "infographic", "review", "vs", "comparison"}

    def get_words(text):
        if not text:
            return set()
        clean = "".join([c.lower() if c.isalnum() or c.isspace() else " " for c in text])
        return {w for w in clean.split() if w and w not in STOPWORDS}

    # Pre-tokenize database content assets and check for metadata flags
    pretokenized_contents = []
    for c_id, c_title, c_type, c_cat_id, c_intent_id in content_rows:
        title_lower = (c_title or "").lower()
        has_vs = "vs" in title_lower or "comparison" in title_lower
        has_review = "review" in title_lower
        has_guide = "guide" in title_lower
        pretokenized_contents.append((
            c_id, c_title, c_type, c_cat_id, c_intent_id,
            get_words(c_title), has_vs, has_review, has_guide
        ))

    # Pre-tokenize database items and check for metadata flags
    pretokenized_items = []
    for i_id, i_name, i_cat_id, i_brand_id in item_rows:
        name_lower = (i_name or "").lower()
        has_vs = "vs" in name_lower or "comparison" in name_lower
        has_review = "review" in name_lower
        has_guide = "guide" in name_lower
        pretokenized_items.append((
            i_id, i_name, i_cat_id, i_brand_id,
            get_words(i_name), has_vs, has_review, has_guide
        ))

    def compute_similarity_opt(
        idea_words, idea_has_vs, idea_has_review, idea_has_guide,
        asset_title, asset_words, asset_has_vs, asset_has_review, asset_has_guide,
        target_name, asset_cat_id, asset_brand_id=None
    ):
        if not idea_words or not asset_words:
            return 0.0
            
        intersection = idea_words.intersection(asset_words)
        union = idea_words.union(asset_words)
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Adjustments
        bonus = 0.0
        # Category bonus
        if asset_cat_id and cat_id_to_name.get(asset_cat_id) == target_name:
            bonus += 0.25
        # Brand bonus
        if asset_brand_id and brand_id_to_name.get(asset_brand_id) == target_name:
            bonus += 0.25
            
        # Intent overlap
        if idea_has_vs and asset_has_vs:
            bonus += 0.25
        if idea_has_review and asset_has_review:
            bonus += 0.25
        if idea_has_guide and asset_has_guide:
            bonus += 0.25
            
        return max(0.0, min(1.0, jaccard + bonus))

    mapped_output = []

    for item in content_strategy_data:
        entity = item["entity"]
        etype = item["type"]
        score = item["opportunity_score"]
        
        youtube_ideas = item.get("youtube", [])
        pinterest_ideas = item.get("pinterest", [])
        blog_ideas = item.get("blog", [])
        
        # Pre-tokenize idea titles and check flags
        def prep_idea(idea_title):
            title_lower = idea_title.lower()
            return (
                idea_title,
                get_words(idea_title),
                "vs" in title_lower or "comparison" in title_lower,
                "review" in title_lower,
                "guide" in title_lower
            )
        
        yt_idea_info = [prep_idea(idea) for idea in youtube_ideas]
        blog_idea_info = [prep_idea(idea) for idea in blog_ideas]
        pin_idea_info = [prep_idea(idea) for idea in pinterest_ideas]
        all_idea_info = yt_idea_info + blog_idea_info
        
        existing_assets = []
        has_youtube_match = False
        has_pinterest_match = False
        has_blog_match = False
        
        # 1. Match against existing database Content (articles & videos)
        for c_id, c_title, c_type, c_cat_id, c_intent_id, c_words, c_has_vs, c_has_review, c_has_guide in pretokenized_contents:
            max_sim = 0.0
            matched_idea_type = None
            
            # Check YouTube ideas
            for idea, i_words, i_has_vs, i_has_review, i_has_guide in yt_idea_info:
                sim = compute_similarity_opt(
                    i_words, i_has_vs, i_has_review, i_has_guide,
                    c_title, c_words, c_has_vs, c_has_review, c_has_guide,
                    entity, c_cat_id
                )
                if sim > max_sim:
                    max_sim = sim
                    matched_idea_type = "youtube"
                    
            # Check Blog ideas
            for idea, i_words, i_has_vs, i_has_review, i_has_guide in blog_idea_info:
                sim = compute_similarity_opt(
                    i_words, i_has_vs, i_has_review, i_has_guide,
                    c_title, c_words, c_has_vs, c_has_review, c_has_guide,
                    entity, c_cat_id
                )
                if sim > max_sim:
                    max_sim = sim
                    matched_idea_type = "blog"

            # Check Pinterest ideas
            for idea, i_words, i_has_vs, i_has_review, i_has_guide in pin_idea_info:
                sim = compute_similarity_opt(
                    i_words, i_has_vs, i_has_review, i_has_guide,
                    c_title, c_words, c_has_vs, c_has_review, c_has_guide,
                    entity, c_cat_id
                )
                if sim > max_sim:
                    max_sim = sim
                    matched_idea_type = "pinterest"
                    
            if max_sim >= 0.40:
                if max_sim >= 0.75:
                    action = "reuse"
                else:
                    action = "update"
                    
                # Cross-platform repurpose check
                if c_type == "article" and matched_idea_type == "youtube":
                    action = "repurpose"
                elif c_type == "video" and matched_idea_type == "blog":
                    action = "repurpose"
                    
                if matched_idea_type == "youtube":
                    has_youtube_match = True
                elif matched_idea_type == "pinterest":
                    has_pinterest_match = True
                elif matched_idea_type == "blog":
                    has_blog_match = True
                    
                if not any(a["id"] == f"content_{c_id}" for a in existing_assets):
                    existing_assets.append({
                        "id": f"content_{c_id}",
                        "type": "video" if c_type == "video" else "article",
                        "title": c_title,
                        "relevance_score": round(max_sim, 2),
                        "action": action
                    })

        # 2. Match against Item product pages
        for i_id, i_name, i_cat_id, i_brand_id, i_words, i_has_vs, i_has_review, i_has_guide in pretokenized_items:
            max_sim = 0.0
            for idea, i_words_idea, i_has_vs_idea, i_has_review_idea, i_has_guide_idea in all_idea_info:
                sim = compute_similarity_opt(
                    i_words_idea, i_has_vs_idea, i_has_review_idea, i_has_guide_idea,
                    i_name, i_words, i_has_vs, i_has_review, i_has_guide,
                    entity, i_cat_id, i_brand_id
                )
                if sim > max_sim:
                    max_sim = sim
                    
            if max_sim >= 0.40:
                action = "reuse" if max_sim >= 0.75 else "update"
                if not any(a["id"] == f"item_{i_id}" for a in existing_assets):
                    existing_assets.append({
                        "id": f"item_{i_id}",
                        "type": "product_page",
                        "title": i_name,
                        "relevance_score": round(max_sim, 2),
                        "action": action
                    })

        # 3. Detect gaps and missing assets
        missing_assets = []
        
        if score >= 0.70:
            priority = "high"
        elif score >= 0.45:
            priority = "medium"
        else:
            priority = "low"
            
        if not has_youtube_match:
            missing_assets.append({
                "content_type": "youtube",
                "missing_topic": f"Video guide, review, or comparison for {entity}",
                "priority": priority
            })
            
        if not has_pinterest_match:
            missing_assets.append({
                "content_type": "pinterest",
                "missing_topic": f"Visual infographic and saveable specifications cheat sheet for {entity}",
                "priority": priority
            })
            
        if not has_blog_match:
            missing_assets.append({
                "content_type": "blog",
                "missing_topic": f"Detailed SEO articles and intent-focused comparisons for {entity}",
                "priority": priority
            })

        existing_assets.sort(key=lambda x: x["relevance_score"], reverse=True)

        mapped_output.append({
            "entity": entity,
            "type": etype,
            "opportunity_score": score,
            "existing_assets": existing_assets,
            "missing_assets": missing_assets
        })
        
    return mapped_output
