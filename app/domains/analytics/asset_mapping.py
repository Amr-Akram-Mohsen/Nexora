# app/domains/interaction/service/insights/asset_mapping.py
from sqlalchemy import select
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.taxonomy.models import Category, Brand
from app.domains.distribution.models import DistributionPost, DistributionPlatform

def map_content_strategy_to_assets(content_strategy_data):
    """
    Maps content strategy suggestions to existing database assets (Articles, Videos, Product pages)
    detects reusable/updateable/repurposeable assets, and identifies missing content gaps.
    
    This acts as the bridge between content strategy generation and asset reality.
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

    dist_posts = db.session.execute(
        select(DistributionPost, DistributionPlatform.name)
        .join(DistributionPlatform)
    ).all()
    
    dist_map = {}
    for post, platform_name in dist_posts:
        key = (post.source_target_type, post.source_target_id)
        if key not in dist_map:
            dist_map[key] = []
        dist_map[key].append({
            "platform": platform_name,
            "status": post.status,
            "publish_date": post.publish_date.isoformat() if post.publish_date else None,
            "views": post.views_count,
            "post_id": post.id
        })

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
        idea_title, idea_words, idea_has_vs, idea_has_review, idea_has_guide,
        asset_title, asset_words, asset_has_vs, asset_has_review, asset_has_guide,
        target_name, asset_cat_id, asset_brand_id=None
    ):
        """
        Computes a stable, semantic similarity score between a content idea and a database asset.
        Combines token Jaccard overlap, exact entity name substring matches, category alignment,
        and intent overlap with mismatch penalties for robust and predictable decisions.
        """
        if not idea_words or not asset_words:
            return 0.0
            
        # 1. Base Jaccard semantic overlap of tokenized words
        intersection = idea_words.intersection(asset_words)
        union = idea_words.union(asset_words)
        jaccard = len(intersection) / len(union) if union else 0.0
        
        score = jaccard
        
        # 2. Entity name substring match (strong signal)
        target_name_lower = target_name.lower()
        asset_title_lower = asset_title.lower()
        if target_name_lower in asset_title_lower:
            score += 0.30
        else:
            # Check individual word intersection of target name
            target_words = {w for w in target_name_lower.split() if len(w) > 2}
            if target_words.intersection(asset_words):
                score += 0.15
                
        # 3. Category/Brand taxonomy alignment
        if asset_cat_id and cat_id_to_name.get(asset_cat_id) == target_name:
            score += 0.20
        if asset_brand_id and brand_id_to_name.get(asset_brand_id) == target_name:
            score += 0.20
            
        # 4. Intent detection consistency & mismatch penalty
        mismatch_penalty = 0.0
        
        # Comparison vs vs
        if idea_has_vs == asset_has_vs:
            if idea_has_vs:
                score += 0.15
        else:
            mismatch_penalty += 0.10
            
        # Review vs review
        if idea_has_review == asset_has_review:
            if idea_has_review:
                score += 0.15
        else:
            mismatch_penalty += 0.10
            
        # Guide vs guide
        if idea_has_guide == asset_has_guide:
            if idea_has_guide:
                score += 0.15
        else:
            mismatch_penalty += 0.10
            
        score -= mismatch_penalty
        
        # Cap relevance score between 0.0 and 1.0
        return max(0.0, min(1.0, score))

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
        
        # Track maximum similarity seen per platform for this entity to aid gap diagnosis
        yt_max_sim = 0.0
        blog_max_sim = 0.0
        pin_max_sim = 0.0
        
        # 1. Match against existing database Content (articles & videos)
        for c_id, c_title, c_type, c_cat_id, c_intent_id, c_words, c_has_vs, c_has_review, c_has_guide in pretokenized_contents:
            max_sim = 0.0
            matched_idea_type = None
            
            # Check YouTube ideas
            for idea, i_words, i_has_vs, i_has_review, i_has_guide in yt_idea_info:
                sim = compute_similarity_opt(
                    idea, i_words, i_has_vs, i_has_review, i_has_guide,
                    c_title, c_words, c_has_vs, c_has_review, c_has_guide,
                    entity, c_cat_id
                )
                if sim > max_sim:
                    max_sim = sim
                    matched_idea_type = "youtube"
                    
            # Check Blog ideas
            for idea, i_words, i_has_vs, i_has_review, i_has_guide in blog_idea_info:
                sim = compute_similarity_opt(
                    idea, i_words, i_has_vs, i_has_review, i_has_guide,
                    c_title, c_words, c_has_vs, c_has_review, c_has_guide,
                    entity, c_cat_id
                )
                if sim > max_sim:
                    max_sim = sim
                    matched_idea_type = "blog"

            # Check Pinterest ideas
            for idea, i_words, i_has_vs, i_has_review, i_has_guide in pin_idea_info:
                sim = compute_similarity_opt(
                    idea, i_words, i_has_vs, i_has_review, i_has_guide,
                    c_title, c_words, c_has_vs, c_has_review, c_has_guide,
                    entity, c_cat_id
                )
                if sim > max_sim:
                    max_sim = sim
                    matched_idea_type = "pinterest"
            
            # Update diagnostic similarity counters
            if matched_idea_type == "youtube":
                yt_max_sim = max(yt_max_sim, max_sim)
            elif matched_idea_type == "blog":
                blog_max_sim = max(blog_max_sim, max_sim)
            elif matched_idea_type == "pinterest":
                pin_max_sim = max(pin_max_sim, max_sim)
                    
            if max_sim >= 0.40:
                # Platform compatibility check
                platform_matches = (
                    (matched_idea_type == "youtube" and c_type == "video") or
                    (matched_idea_type in ["blog", "pinterest"] and c_type == "article")
                )
                
                # Refine decision logic: reuse (high confidence + platform match),
                # update (medium confidence + platform match), repurpose (platform mismatch)
                if platform_matches:
                    if max_sim >= 0.75:
                        action = "reuse"
                    else:
                        action = "update"
                else:
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
                        "action": action,
                        "distribution_posts": dist_map.get(("content", c_id), [])
                    })

        # 2. Match against Item product pages
        for i_id, i_name, i_cat_id, i_brand_id, i_words, i_has_vs, i_has_review, i_has_guide in pretokenized_items:
            max_sim = 0.0
            for idea, i_words_idea, i_has_vs_idea, i_has_review_idea, i_has_guide_idea in all_idea_info:
                sim = compute_similarity_opt(
                    idea, i_words_idea, i_has_vs_idea, i_has_review_idea, i_has_guide_idea,
                    i_name, i_words, i_has_vs, i_has_review, i_has_guide,
                    entity, i_cat_id, i_brand_id
                )
                if sim > max_sim:
                    max_sim = sim
            
            # Update diagnostic similarity counters for fallback checking
            yt_max_sim = max(yt_max_sim, max_sim)
            blog_max_sim = max(blog_max_sim, max_sim)
                    
            if max_sim >= 0.40:
                action = "reuse" if max_sim >= 0.75 else "update"
                if not any(a["id"] == f"item_{i_id}" for a in existing_assets):
                    existing_assets.append({
                        "id": f"item_{i_id}",
                        "type": "product_page",
                        "title": i_name,
                        "relevance_score": round(max_sim, 2),
                        "action": action,
                        "distribution_posts": dist_map.get(("item", i_id), [])
                    })

        # 3. Detect gaps and missing assets with explanatory diagnostics
        missing_assets = []
        
        # Priority mapping
        if score >= 0.70:
            priority = "high"
            priority_justification = f"High opportunity score ({score:.2f}) indicates severe content coverage gap relative to high user demand."
        elif score >= 0.45:
            priority = "medium"
            priority_justification = f"Medium opportunity score ({score:.2f}) warrants strategic coverage expansion to capture untapped search demand."
        else:
            priority = "low"
            priority_justification = f"Low priority opportunity score ({score:.2f}). Create assets as secondary focus after addressing high priority gaps."
            
        # Helper to dynamically diagnose gap reasons
        def diagnose_gap_reason(platform, max_sim, has_other_match):
            if max_sim > 0.0 and max_sim < 0.40:
                return "Low relevance match: database assets exist with similar keywords, but they lack the specific intent (comparison/review/guide) required by the content strategy."
            elif has_other_match:
                return f"Platform mismatch: written content or visual assets exist in database, but corresponding {platform} coverage is missing."
            else:
                return "Zero coverage: no existing database articles, videos, or product pages match the target entity name or category taxonomy."

        if not has_youtube_match:
            missing_assets.append({
                "content_type": "youtube",
                "missing_topic": f"Video guide, review, or comparison for {entity}",
                "priority": priority,
                "reason": diagnose_gap_reason("YouTube (video-first)", yt_max_sim, has_blog_match or has_pinterest_match),
                "priority_justification": priority_justification
            })
            
        if not has_pinterest_match:
            missing_assets.append({
                "content_type": "pinterest",
                "missing_topic": f"Visual infographic and saveable specifications cheat sheet for {entity}",
                "priority": priority,
                "reason": diagnose_gap_reason("Pinterest (visual cheat-sheet)", pin_max_sim, has_blog_match or has_youtube_match),
                "priority_justification": priority_justification
            })
            
        if not has_blog_match:
            missing_assets.append({
                "content_type": "blog",
                "missing_topic": f"Detailed SEO articles and intent-focused comparisons for {entity}",
                "priority": priority,
                "reason": diagnose_gap_reason("Blog (search intent SEO)", blog_max_sim, has_youtube_match or has_pinterest_match),
                "priority_justification": priority_justification
            })

        existing_assets.sort(key=lambda x: x["relevance_score"], reverse=True)

        # 4. Structured downstream Content Engine metadata
        content_planning = {
            "lifecycle_tag": item.get("lifecycle_tag", "evergreen"),
            "priority_score": item.get("priority_score", score * 100),
            "target_audience": "Informational searchers" if etype == "category" else "Commercial intent buyers"
        }
        publishing_decisions = {
            "primary_action": "create" if missing_assets else ("update" if any(a["action"] == "update" for a in existing_assets) else "reuse"),
            "urgency_level": "immediate" if score >= 0.70 else ("scheduled" if score >= 0.45 else "backlog")
        }
        platform_strategy = {
            "primary_platform": "youtube" if etype == "brand" else "blog",
            "recommended_angle": item.get("content_angle", "guide")
        }

        mapped_output.append({
            "entity": entity,
            "type": etype,
            "opportunity_score": score,
            "existing_assets": existing_assets,
            "missing_assets": missing_assets,
            "content_planning": content_planning,
            "publishing_decisions": publishing_decisions,
            "platform_strategy": platform_strategy
        })
        
    return mapped_output
