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

def get_decision_intelligence_data(lightweight=False):
    """
    Combines demand, coverage, and engagement signals to calculate normalized opportunity scores
    and generate prioritised Top Opportunities and an Action Queue.
    """
    categories_data = get_content_coverage_matrix()
    brands_data = get_brand_opportunity_data()
    intent_data = get_intent_opportunity_data()
    
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
        item.pop("score", None)

    rec_perf = get_recommendation_performance_data()
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
