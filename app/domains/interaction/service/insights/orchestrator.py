# app/domains/interaction/service/insights/orchestrator.py
from app.domains.interaction.service.insights.opportunities import (
    get_content_coverage_matrix,
    get_brand_opportunity_data,
    get_intent_opportunity_data,
    get_recommendation_performance_data
)
from app.domains.interaction.service.insights.learning_memory import load_memory_layer
from app.domains.interaction.service.insights.performance_feedback import evaluate_content_performance_feedback
from app.domains.interaction.service.insights.content_strategy import generate_content_strategy
from app.domains.interaction.service.insights.asset_mapping import map_content_strategy_to_assets
from app.domains.interaction.service.insights.publishing_plan import generate_content_publishing_plan
from app.domains.interaction.service.insights.autonomous_execution import generate_execution_plan
from app.domains.interaction.service.insights.governance import generate_execution_governance_layer
def _generate_computed_strategy(name, entity_type, reason, related_content_ctr):
    prefer_comparisons = related_content_ctr < 5.0
    
    reason_lower = reason.lower()
    if "high demand + low coverage" in reason_lower or "high demand + low coverage gap" in reason_lower:
        strategic_intent = "priority content creation"
        content_angle = "guide"
    elif "high engagement + low content" in reason_lower:
        strategic_intent = "fast content gap exploitation"
        content_angle = "comparison"
    elif "high engagement" in reason_lower:
        strategic_intent = "reinforcement / expansion content"
        content_angle = "review"
    else:
        strategic_intent = "reinforcement / expansion content"
        content_angle = "trend analysis"

    # YouTube video ideas (2-3 titles)
    if entity_type.lower() == "category":
        if prefer_comparisons:
            youtube_ideas = [
                f"Ultimate {name} Comparison: Which One Should You Buy?",
                f"Top 5 {name} Face-Off & Performance Review",
                f"Testing the Cheapest vs Most Expensive {name}"
            ]
        else:
            youtube_ideas = [
                f"Complete {name} Buying Guide: Don't Buy Until You Watch This!",
                f"Top 10 Best {name} of the Year: The Definitive List",
                f"How to Choose Your First {name} (Step-by-Step)"
            ]
    else: # brand
        if prefer_comparisons:
            youtube_ideas = [
                f"{name} vs The Competition: Is It Worth the Premium Price?",
                f"Testing {name} Products: Honest Comparison & Review"
            ]
        else:
            youtube_ideas = [
                f"The Complete Guide to {name} Products: Features & Setup",
                f"Unboxing & First Look: Newest Releases from {name}"
            ]

    # Pinterest pin ideas (1-2 concepts)
    if entity_type.lower() == "category":
        pinterest_ideas = [
            f"How to Choose the Perfect {name} (Infographic Guide)",
            f"The Ultimate {name} Cheat Sheet & Specifications Comparison Checklist"
        ]
    else:
        pinterest_ideas = [
            f"Visual Guide: Evolution of {name} Top Models",
            f"{name} Product Selection Cheat Sheet (Infographic)"
        ]

    # Blog article idea (1 SEO title)
    if entity_type.lower() == "category":
        if content_angle == "guide":
            blog_article_idea = f"The Ultimate {name} Buying Guide & Expert Recommendations"
        elif content_angle == "comparison":
            blog_article_idea = f"Direct Comparison: Head-to-Head {name} Review"
        elif content_angle == "review":
            blog_article_idea = f"In-Depth Review: Analyzing the Top-Rated {name} in Saudi Arabia"
        else:
            blog_article_idea = f"5 Critical Features to Look for in a Modern {name}"
    else:
        if content_angle == "review":
            blog_article_idea = f"Expert Review: Are {name} Products Actually Worth It?"
        else:
            blog_article_idea = f"Buying Guide: Top 5 Best {name} Deals & Specifications"

    return {
        "youtube_ideas": youtube_ideas,
        "youtube_video_ideas": youtube_ideas,
        "pinterest_ideas": pinterest_ideas,
        "pinterest_pin_ideas": pinterest_ideas,
        "blog_article_idea": blog_article_idea,
        "content_angle": content_angle,
        "strategic_intent": strategic_intent
    }


def _generate_computed_action_strategy(target, type_str, action_title, priority, confidence, impact):
    is_buying_guide = "buying" in action_title.lower() or "guide" in action_title.lower()
    is_brand_expansion = "brand" in type_str.lower() or "brand" in action_title.lower()
    is_high_confidence = confidence >= 0.85
    
    if is_buying_guide:
        content_angle = "guide"
        if is_high_confidence:
            youtube = [
                f"Ultimate Video Guide: Best {target} of 2026",
                f"Watch This Before Buying {target}! (Video Review)"
            ]
            blog = f"SEO Guide: The Definitive {target} Analysis & Search Trends"
            pinterest = [
                f"Cheat Sheet: {target} Video-First Setup & Specs Guide",
                f"Step-by-Step {target} Tutorial & Video Tips"
            ]
        else:
            youtube = [
                f"Best {target} to Buy in 2026: Expert Buying Guide",
                f"5 Mistakes to Avoid When Buying {target}"
            ]
            blog = f"The Ultimate {target} Buying Guide & Selection Tips"
            pinterest = [
                f"Infographic: How to Choose the Best {target}",
                f"{target} Selection Cheat Sheet for Beginners"
            ]
    elif is_brand_expansion:
        content_angle = "comparison"
        if is_high_confidence:
            youtube = [
                f"Hands-On Video Review: Testing {target} Performance",
                f"Ultimate {target} Brand Comparison (Watch Before Buying)"
            ]
            blog = f"SEO Review: Are {target} Products Worth the Investment?"
            pinterest = [
                f"Must-Watch Video Guide: {target} Specifications Table",
                f"Visual comparison: {target} vs Competitors (Infographic)"
            ]
        else:
            youtube = [
                f"{target} Review: Is It Actually Worth the Premium Price?",
                f"{target} vs The Competition: Head-to-Head Comparison"
            ]
            blog = f"In-Depth Review: Analyzing {target} Products & Alternatives"
            pinterest = [
                f"Visual Guide: {target} Brand Specifications Comparison",
                f"Pros & Cons: Honest {target} Review Checklist"
            ]
    else:
        # Fallback
        if is_high_confidence:
            content_angle = "trend analysis"
            youtube = [
                f"Ultimate Video Walkthrough: Master {target} Today",
                f"Market Trends: Future of {target} (Watch Now)"
            ]
            blog = f"SEO Trend Report: In-Depth {target} Industry Analysis"
            pinterest = [
                f"Visual Guide: Future Trends of {target}",
                f"Cheat Sheet: Mastering {target} in 2026"
            ]
        else:
            content_angle = "trend analysis"
            youtube = [
                f"New Trends in {target}: What's Changing?",
                f"How to Master {target} in 2026"
            ]
            blog = f"Top {target} Trends & Comprehensive Market Analysis"
            pinterest = [
                f"{target} Trend Highlights & Style Guide",
                f"Infographic: {target} Cheat Sheet"
            ]
            
    return {
        "youtube_ideas": youtube,
        "youtube_video_ideas": youtube,
        "blog_article_idea": blog,
        "seo_blog_article_title": blog,
        "pinterest_ideas": pinterest,
        "pinterest_content_ideas": pinterest,
        "content_angle": content_angle,
        "suggested_content_angle": content_angle
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
        for item in eval_results:
            ent = item["entity"]
            eval_val = item["evaluation"]
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
        
        norm_demand = (demand_val / max_cat_demand) if max_cat_demand > 0 else 0.0
        norm_coverage_gap = 1.0 - ((content_val / max_cat_content) if max_cat_content > 0 else 0.0)
        norm_eng = (avg_eng_val / max_cat_avg_eng) if max_cat_avg_eng > 0 else 0.0
        
        base_score = 0.4 * norm_demand + 0.4 * norm_coverage_gap + 0.2 * norm_eng
        
        perf_feedback = entity_avg_feedback.get(c["name"], 0.5)
        score = 0.7 * base_score + 0.3 * perf_feedback
        score = round(max(0.0, min(1.0, score)), 2)
        
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
        
        norm_demand = (demand_val / max_brand_demand) if max_brand_demand > 0 else 0.0
        norm_coverage_gap = 1.0 - ((content_val / max_brand_content) if max_brand_content > 0 else 0.0)
        norm_eng = (avg_eng_val / max_brand_avg_eng) if max_brand_avg_eng > 0 else 0.0
        
        base_score = 0.4 * norm_demand + 0.4 * norm_coverage_gap + 0.2 * norm_eng
        
        perf_feedback = entity_avg_feedback.get(b["name"], 0.5)
        score = 0.7 * base_score + 0.3 * perf_feedback
        score = round(max(0.0, min(1.0, score)), 2)
        
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
        opp["content_strategy"] = _generate_computed_strategy(
            opp["entity"],
            opp["type"],
            opp["reason"],
            related_content_ctr
        )

    # 4. Insight Actions Queue
    action_queue = []
    intent_map = {item["category_name"]: item for item in intent_data}
    
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
    for item in action_queue:
        item["content_output"] = _generate_computed_action_strategy(
            item["target"],
            item["type"],
            item["title"],
            item["priority"],
            item["confidence"],
            item["impact"]
        )
        item.pop("score", None)

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
