# app/application/interaction/get_insights.py
from app.domains.analytics import (
    get_intent_opportunity_data,
    get_brand_opportunity_data,
    get_recommendation_performance_data,
    get_content_coverage_matrix,
    get_decision_intelligence_data
)

def get_insights_workflow(time_frame: str):
    """
    Orchestrates the retrieval of editorial intelligence decision-making metrics:
    1. Intent Opportunity Analysis
    2. Brand Opportunity Analysis
    3. Recommendation Performance
    4. Content Coverage Matrix
    5. Scoring, Unified Ranks, and Action Queue
    """
    intent_opportunities = get_intent_opportunity_data()
    brand_opportunities = get_brand_opportunity_data()
    recommendation_performance = get_recommendation_performance_data()
    coverage_matrix = get_content_coverage_matrix()
    decision_data = get_decision_intelligence_data(lightweight=True)

    return {
        "intent_opportunities": intent_opportunities,
        "brand_opportunities": brand_opportunities,
        "recommendation_performance": recommendation_performance,
        "coverage_matrix": coverage_matrix,
        "opportunity_scores": decision_data["opportunity_scores"],
        "top_opportunities": decision_data["top_opportunities"],
        "action_queue": decision_data["action_queue"],
        "content_strategy": decision_data.get("content_strategy", []),
        "content_asset_mapping": decision_data.get("content_asset_mapping", []),
        "content_publishing_plan": decision_data.get("content_publishing_plan", {}),
        "content_performance_feedback": decision_data.get("content_performance_feedback", {}),
        "execution_plan": decision_data.get("execution_plan", {}),
        "execution_governance": decision_data.get("execution_governance", {})
    }

