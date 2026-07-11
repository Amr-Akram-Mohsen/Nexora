# app/domains/interaction/service/insights/orchestrator.py
from app.domains.analytics.content_opportunities import (
    get_content_coverage_matrix,
    get_intent_opportunity_data
)
from app.domains.analytics.product_opportunities import get_brand_opportunity_data
from app.domains.analytics.recommendation_performance import get_recommendation_performance_data
from app.domains.analytics.learning_memory import load_memory_layer
from app.domains.analytics.performance_feedback import evaluate_content_performance_feedback
from app.domains.analytics.content_strategy import generate_content_strategy
from app.domains.analytics.asset_mapping import map_content_strategy_to_assets
from app.domains.analytics.publishing_plan import generate_content_publishing_plan
from app.domains.analytics.autonomous_execution import generate_execution_plan
from app.domains.analytics.governance import generate_execution_governance_layer
from app.domains.analytics.shared import score_opportunity_entity, select_primary_platform

def _generate_content_ideas(
    entity: str,
    entity_type: str,
    intent_signal: str,
    confidence: float = 0.5,
    related_content_ctr: float = 5.0
) -> dict:
    intent_lower = intent_signal.lower()
    is_buying_guide = "buying" in intent_lower or "guide" in intent_lower or "high demand + low coverage" in intent_lower or "high demand + low coverage gap" in intent_lower
    is_brand_expansion = "brand" in entity_type.lower() or "brand" in intent_lower or "high engagement + low content" in intent_lower
    is_high_confidence = confidence >= 0.85
    prefer_comparisons = related_content_ctr < 5.0
    
    # 1. Determine content angle & strategic intent
    if is_buying_guide:
        content_angle = "guide"
        strategic_intent = "priority content creation"
    elif is_brand_expansion:
        content_angle = "comparison"
        strategic_intent = "fast content gap exploitation"
    elif "review" in intent_lower or "high engagement" in intent_lower:
        content_angle = "review"
        strategic_intent = "reinforcement / expansion content"
    else:
        content_angle = "trend analysis"
        strategic_intent = "reinforcement / expansion content"

    # 2. Generate Youtube, Pinterest, Blog ideas
    youtube = []
    pinterest = []
    blog = ""
    
    if entity_type.lower() == "category":
        if content_angle == "guide":
            if is_high_confidence:
                youtube = [
                    f"Ultimate Video Guide: Best {entity} of 2026",
                    f"Watch This Before Buying {entity}! (Video Review)"
                ]
                blog = f"SEO Guide: The Definitive {entity} Analysis & Search Trends"
                pinterest = [
                    f"Cheat Sheet: {entity} Video-First Setup & Specs Guide",
                    f"Step-by-Step {entity} Tutorial & Video Tips"
                ]
            else:
                youtube = [
                    f"Best {entity} to Buy in 2026: Expert Buying Guide",
                    f"5 Mistakes to Avoid When Buying {entity}"
                ]
                blog = f"The Ultimate {entity} Buying Guide & Selection Tips"
                pinterest = [
                    f"Infographic: How to Choose the Best {entity}",
                    f"{entity} Selection Cheat Sheet for Beginners"
                ]
        elif content_angle == "comparison":
            if is_high_confidence:
                youtube = [
                    f"Hands-On Video Review: Testing {entity} Performance",
                    f"Ultimate {entity} Brand Comparison (Watch Before Buying)"
                ]
                blog = f"SEO Review: Are {entity} Products Worth the Investment?"
                pinterest = [
                    f"Must-Watch Video Guide: {entity} Specifications Table",
                    f"Visual comparison: {entity} vs Competitors (Infographic)"
                ]
            else:
                youtube = [
                    f"{entity} Review: Is It Actually Worth the Premium Price?",
                    f"{entity} vs The Competition: Head-to-Head Comparison"
                ]
                blog = f"In-Depth Review: Analyzing {entity} Products & Alternatives"
                pinterest = [
                    f"Visual Guide: {entity} Brand Specifications Comparison",
                    f"Pros & Cons: Honest {entity} Review Checklist"
                ]
        else: # review / trend analysis
            if is_high_confidence:
                youtube = [
                    f"Ultimate Video Walkthrough: Master {entity} Today",
                    f"Market Trends: Future of {entity} (Watch Now)"
                ]
                blog = f"SEO Trend Report: In-Depth {entity} Industry Analysis"
                pinterest = [
                    f"Visual Guide: Future Trends of {entity}",
                    f"Cheat Sheet: Mastering {entity} in 2026"
                ]
            else:
                youtube = [
                    f"New Trends in {entity}: What's Changing?",
                    f"How to Master {entity} in 2026"
                ]
                blog = f"Top {entity} Trends & Comprehensive Market Analysis"
                pinterest = [
                    f"{entity} Trend Highlights & Style Guide",
                    f"Infographic: {entity} Cheat Sheet"
                ]
    else: # Brand (or other)
        if content_angle == "guide":
            if is_high_confidence:
                youtube = [
                    f"Ultimate Video Guide: Best {entity} of 2026",
                    f"Watch This Before Buying {entity}! (Video Review)"
                ]
                blog = f"SEO Guide: The Definitive {entity} Analysis & Search Trends"
                pinterest = [
                    f"Cheat Sheet: {entity} Video-First Setup & Specs Guide",
                    f"Step-by-Step {entity} Tutorial & Video Tips"
                ]
            else:
                youtube = [
                    f"Best {entity} to Buy in 2026: Expert Buying Guide",
                    f"5 Mistakes to Avoid When Buying {entity}"
                ]
                blog = f"The Ultimate {entity} Buying Guide & Selection Tips"
                pinterest = [
                    f"Infographic: How to Choose the Best {entity}",
                    f"{entity} Selection Cheat Sheet for Beginners"
                ]
        elif content_angle == "comparison" or content_angle == "review":
            if prefer_comparisons:
                youtube = [
                    f"{entity} vs The Competition: Is It Worth the Premium Price?",
                    f"Testing {entity} Products: Honest Comparison & Review"
                ]
            else:
                youtube = [
                    f"The Complete Guide to {entity} Products: Features & Setup",
                    f"Unboxing & First Look: Newest Releases from {entity}"
                ]
            
            if is_high_confidence:
                blog = f"SEO Review: Are {entity} Products Worth the Investment?"
                pinterest = [
                    f"Must-Watch Video Guide: {entity} Specifications Table",
                    f"Visual comparison: {entity} vs Competitors (Infographic)"
                ]
            else:
                blog = f"Expert Review: Are {entity} Products Actually Worth It?"
                pinterest = [
                    f"Visual Guide: Evolution of {entity} Top Models",
                    f"{entity} Product Selection Cheat Sheet (Infographic)"
                ]
        else: # trend analysis / fallback
            if is_high_confidence:
                youtube = [
                    f"Ultimate Video Walkthrough: Master {entity} Today",
                    f"Market Trends: Future of {entity} (Watch Now)"
                ]
                blog = f"SEO Trend Report: In-Depth {entity} Industry Analysis"
                pinterest = [
                    f"Visual Guide: Future Trends of {entity}",
                    f"Cheat Sheet: Mastering {entity} in 2026"
                ]
            else:
                youtube = [
                    f"New Trends in {entity}: What's Changing?",
                    f"How to Master {entity} in 2026"
                ]
                blog = f"Top {entity} Trends & Comprehensive Market Analysis"
                pinterest = [
                    f"{entity} Trend Highlights & Style Guide",
                    f"Infographic: {entity} Cheat Sheet"
                ]

    platform = select_primary_platform(entity_type, intent_signal)
    
    if platform == "youtube":
        action = youtube[0] if youtube else f"Create video for {entity}"
    elif platform == "pinterest":
        action = pinterest[0] if pinterest else f"Create pin for {entity}"
    else:
        action = blog if blog else f"Write article for {entity}"

    return {
        "youtube": youtube,
        "youtube_ideas": youtube,
        "youtube_video_ideas": youtube,
        
        "pinterest": pinterest,
        "pinterest_ideas": pinterest,
        "pinterest_pin_ideas": pinterest,
        "pinterest_content_ideas": pinterest,
        
        "blog": [blog] if blog else [],
        "blog_ideas": [blog] if blog else [],
        "blog_article_idea": blog,
        "seo_blog_article_title": blog,
        
        "content_angle": content_angle,
        "suggested_content_angle": content_angle,
        "strategic_intent": strategic_intent,
        
        "topic": entity,
        "platform": platform,
        "action": action
    }



def get_decision_intelligence_data(lightweight=False):
    """
    Combines demand, coverage, and engagement signals to calculate normalized opportunity scores
    and generate prioritised Top Opportunities and an Action Queue.
    """
    categories_data = get_content_coverage_matrix()
    brands_data = get_brand_opportunity_data()
    intent_data = get_intent_opportunity_data()
    rec_perf = get_recommendation_performance_data()
    
    # 0. Content Performance Feedback Loop
    if lightweight:
        feedback_data = {"evaluation_results": [], "average_accuracy": 85.0, "failures_detected": [], "memory_layer": []}
        entity_avg_feedback = {}
        for m in load_memory_layer():
            ent = m["entity"]
            entity_avg_feedback[ent] = 0.8 if m["outcome"] == "success" else 0.2
    else:
        feedback_data = evaluate_content_performance_feedback()
        eval_results = feedback_data["evaluation_results"]
        
        entity_feedback = {}
        for product in eval_results:
            ent = product["entity"]
            eval_val = product["evaluation"]
            if eval_val == "overperforming":
                f_score = 0.9
            elif eval_val == "underperforming":
                f_score = 0.1
            else:
                f_score = 0.5
                
            if ent not in entity_feedback:
                entity_feedback[ent] = []
            entity_feedback[ent].append(f_score)
            
        entity_avg_feedback = {}
        for ent, scores in entity_feedback.items():
            entity_avg_feedback[ent] = sum(scores) / len(scores)
            
        for m in feedback_data.get("memory_layer", []):
            ent = m["entity"]
            if ent not in entity_avg_feedback:
                entity_avg_feedback[ent] = 0.8 if m["outcome"] == "success" else 0.2

    # 1. Category Opportunity Scoring
    max_cat_demand = max([c["demand_score"] for c in categories_data]) if categories_data else 0
    max_cat_content = max([c["content_count"] for c in categories_data]) if categories_data else 0
    
    cat_avg_engagements = []
    for c in categories_data:
        cat_avg_engagements.append(c["demand_score"] / c["content_count"] if c["content_count"] > 0 else 0)
    max_cat_avg_eng = max(cat_avg_engagements) if cat_avg_engagements else 0

    category_scores = {}
    for idx, c in enumerate(categories_data):
        demand_val = c["demand_score"]
        content_val = c["content_count"]
        avg_eng_val = cat_avg_engagements[idx]
        
        score = score_opportunity_entity(
            demand_val=demand_val,
            max_demand=max_cat_demand,
            content_val=content_val,
            max_content=max_cat_content,
            avg_eng=avg_eng_val,
            max_avg_eng=max_cat_avg_eng,
            perf_feedback=entity_avg_feedback.get(c["name"], 0.5)
        )
        
        reason = f"{c['demand']} demand + {c['coverage'].lower()} coverage"
        if c['gap_score'] == "High Gap":
            reason = "High demand + low coverage gap"
            
        category_scores[c["name"]] = {
            "score": score,
            "reason": reason
        }

    # 2. Brand Opportunity Scoring
    max_brand_demand = max([b["engagement"] for b in brands_data]) if brands_data else 0
    max_brand_content = max([b["article_volume"] for b in brands_data]) if brands_data else 0
    
    brand_avg_engagements = []
    for b in brands_data:
        total_vol = b["article_volume"] + b["product_volume"]
        brand_avg_engagements.append(b["engagement"] / total_vol if total_vol > 0 else 0)
    max_brand_avg_eng = max(brand_avg_engagements) if brand_avg_engagements else 0

    brand_scores = {}
    for idx, b in enumerate(brands_data):
        demand_val = b["engagement"]
        content_val = b["article_volume"]
        avg_eng_val = brand_avg_engagements[idx]
        
        score = score_opportunity_entity(
            demand_val=demand_val,
            max_demand=max_brand_demand,
            content_val=content_val,
            max_content=max_brand_content,
            avg_eng=avg_eng_val,
            max_avg_eng=max_brand_avg_eng,
            perf_feedback=entity_avg_feedback.get(b["name"], 0.5)
        )
        
        reason = f"{b['engagement_level']} engagement + low content" if b["opportunity"] else f"{b['engagement_level']} engagement"
        
        brand_scores[b["name"]] = {
            "score": score,
            "reason": reason
        }

    # 3. Top Opportunities Unified Ranking View
    top_opportunities = []
    for name, data in category_scores.items():
        top_opportunities.append({
            "entity": name,
            "type": "Category",
            "score": data["score"],
            "reason": data["reason"]
        })
    for name, data in brand_scores.items():
        top_opportunities.append({
            "entity": name,
            "type": "Brand",
            "score": data["score"],
            "reason": data["reason"]
        })
        
    top_opportunities.sort(key=lambda x: x["score"], reverse=True)
    top_opportunities = top_opportunities[:15]

    # Compute content strategy for each top opportunity
    related_content_ctr = rec_perf.get("related_content_ctr", 0.0)
    for opp in top_opportunities:
        opp["content_strategy"] = _generate_content_ideas(
            opp["entity"],
            opp["type"],
            opp["reason"],
            related_content_ctr=related_content_ctr
        )

    # 4. Insight Actions Queue
    action_queue = []
    intent_map = {product["category_name"]: product for product in intent_data}
    
    # Category actions
    for name, data in category_scores.items():
        score = data["score"]
        if score >= 0.35:
            intent_info = intent_map.get(name)
            action_type = "Content Expansion"
            action_title = f"Expand content in {name}"
            expected_impact = "High traffic capture potential"
            
            if intent_info:
                opt_text = intent_info["opportunity"]
                action_title = f"{opt_text} for {name}"
                action_type = "Content Intent Optimization"
                expected_impact = "Address intent coverage gap to boost CTR"
                
            priority = "High" if score >= 0.70 else ("Medium" if score >= 0.45 else "Low")
            confidence = round(0.70 + (score * 0.25), 2)
            
            action_queue.append({
                "title": action_title,
                "target": name,
                "type": action_type,
                "priority": priority,
                "impact": expected_impact,
                "confidence": confidence,
                "score": score
            })
            
    # Brand actions
    for name, data in brand_scores.items():
        score = data["score"]
        if score >= 0.35:
            priority = "High" if score >= 0.70 else ("Medium" if score >= 0.45 else "Low")
            confidence = round(0.70 + (score * 0.25), 2)
            action_queue.append({
                "title": f"Expand brand reviews and product coverage for {name}",
                "target": name,
                "type": "Brand Expansion",
                "priority": priority,
                "impact": "Monetize high user brand affinity",
                "confidence": confidence,
                "score": score
            })
            
    action_queue.sort(key=lambda x: x["score"], reverse=True)
    for product in action_queue:
        product["content_output"] = _generate_content_ideas(
            product["target"],
            product["type"],
            product["title"],
            confidence=product["confidence"]
        )
        product.pop("score", None)

    recommendation_metrics = {
        "impressions": rec_perf["impressions"],
        "clicks": rec_perf["clicks"],
        "ctr": {
            "related_content": rec_perf["related_content_ctr"],
            "related_product": rec_perf["related_products_ctr"],
            "shop_product": rec_perf["shop_products_ctr"],
            "overall": rec_perf["overall_ctr"]
        },
        "diagnoses": rec_perf["diagnoses"],
        "quality_scores": rec_perf["quality_scores"],
        "benchmarking": rec_perf["benchmarking"]
    }

    opps_payload = {
        "top_opportunities": top_opportunities,
        "categories_data": categories_data,
        "brands_data": brands_data,
        "intent_data": intent_data,
        "recommendation_performance": rec_perf
    }
    if lightweight:
        return {
            "opportunity_scores": {
                "categories": category_scores,
                "brands": brand_scores
            },
            "top_opportunities": top_opportunities,
            "action_queue": action_queue,
            "recommendation_metrics": recommendation_metrics,
            "content_strategy": [],
            "content_asset_mapping": [],
            "content_publishing_plan": {},
            "content_performance_feedback": {},
            "execution_plan": {},
            "execution_governance": {}
        }

    content_strategy = generate_content_strategy(opps_payload)
    content_asset_mapping = map_content_strategy_to_assets(content_strategy)
    content_publishing_plan = generate_content_publishing_plan(content_asset_mapping)
    execution_plan = generate_execution_plan(content_publishing_plan, content_asset_mapping, feedback_data)
    execution_governance = generate_execution_governance_layer(execution_plan, content_asset_mapping, feedback_data)

    return {
        "opportunity_scores": {
            "categories": category_scores,
            "brands": brand_scores
        },
        "top_opportunities": top_opportunities,
        "action_queue": action_queue,
        "recommendation_metrics": recommendation_metrics,
        "content_strategy": content_strategy,
        "content_asset_mapping": content_asset_mapping,
        "content_publishing_plan": content_publishing_plan,
        "content_performance_feedback": feedback_data,
        "execution_plan": execution_plan,
        "execution_governance": execution_governance
    }

def get_executive_summary():
    from app.domains.analytics.content_opportunities import get_content_completeness_report
    from app.domains.analytics.product_opportunities import get_catalog_health_report, get_source_intelligence
    from app.domains.analytics.recommendation_performance import get_recommendation_performance_data
    from app.domains.analytics.distribution_intelligence import get_distribution_intelligence_data
    from app.domains.analytics.performance_feedback import evaluate_content_performance_feedback
    from app.domains.analytics.trends import get_trending_categories_data
    
    comp_report = get_content_completeness_report()
    cat_health = get_catalog_health_report()
    rec_perf = get_recommendation_performance_data()
    dist_intel = get_distribution_intelligence_data()
    
    content_completeness = sum(c["avg_completeness"] for c in comp_report) / max(1, len(comp_report))
    catalog_completeness = sum(c["coverage_rate"] for c in cat_health) / max(1, len(cat_health))
    rec_ctr = rec_perf.get("overall_ctr", 0.0)
    dist_cov = dist_intel.get("system_coverage_rate", 0.0)
    
    norm_ctr = min(100.0, (rec_ctr / 10.0) * 100)
    health_score = (content_completeness + catalog_completeness + norm_ctr + dist_cov) / 4.0
    
    system_health = {
        "score": round(health_score, 1),
        "content_completeness": round(content_completeness, 1),
        "catalog_completeness": round(catalog_completeness, 1),
        "recommendation_ctr": round(rec_ctr, 1),
        "distribution_coverage": round(dist_cov, 1)
    }
    
    dec_data = get_decision_intelligence_data(lightweight=True)
    top_opps = dec_data.get("top_opportunities", [])[:3]
    
    trends = get_trending_categories_data()
    velocity = [
        {"category": t["name"], "velocity": t["growth_percent"], "volume": t["current_volume"]}
        for t in trends[:3]
    ]
    
    feedback = evaluate_content_performance_feedback()
    high_sev = [f for f in feedback.get("failures_detected", []) if f.get("severity") == "high"]
    
    sources = get_source_intelligence()
    stale_sources = [s for s in sources if s.get("staleness_pct", 0) > 50]
    
    dead_links = sum(c["items_missing_links"] for c in cat_health)
    
    risks = {
        "high_severity_underperformers": len(high_sev),
        "stale_sources": len(stale_sources),
        "missing_affiliate_links": dead_links,
        "total_risks": len(high_sev) + len(stale_sources) + dead_links
    }
    
    return {
        "system_health": system_health,
        "top_opportunities": top_opps,
        "engagement_velocity": velocity,
        "risks": risks
    }

