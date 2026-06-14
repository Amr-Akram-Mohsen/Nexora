# app/admin/insights.py
import time
from flask import Blueprint, jsonify, request
from app.core.decorators import admin_required
from app.application.interaction.get_insights import get_insights_workflow
from app.domains.interaction.service.insights import (
    get_decision_intelligence_data,
    get_intent_opportunity_data,
    get_brand_opportunity_data,
    get_recommendation_performance_data,
    get_content_coverage_matrix,
    generate_content_strategy,
    map_content_strategy_to_assets,
    generate_content_publishing_plan,
    evaluate_content_performance_feedback,
    generate_execution_plan,
    generate_execution_governance_layer
)

bp = Blueprint("api_insights", __name__, url_prefix="/admin/insights")

INSIGHTS_CACHE = {
    "strategy": {},
    "assets": {},
    "publishing_plan": {},
    "performance": {},
    "governance": {}
}

# Cache TTL: 10 minutes (600 seconds)
CACHE_TTL = 600


def get_cached(layer, key):
    cache = INSIGHTS_CACHE.get(layer, {})
    if key in cache:
        entry = cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
    return None


def set_cached(layer, key, data):
    if layer not in INSIGHTS_CACHE:
        INSIGHTS_CACHE[layer] = {}
    INSIGHTS_CACHE[layer][key] = {
        "data": data,
        "timestamp": time.time()
    }


def invalidate_cache(layer, key=None):
    if layer == "all":
        for l in INSIGHTS_CACHE:
            if key:
                INSIGHTS_CACHE[l].pop(key, None)
            else:
                INSIGHTS_CACHE[l] = {}
    else:
        if layer in INSIGHTS_CACHE:
            if key:
                INSIGHTS_CACHE[layer].pop(key, None)
            else:
                INSIGHTS_CACHE[layer] = {}


@bp.before_request
@admin_required
def require_admin():
    """Ensure all insights endpoints require admin privilege."""
    pass


@bp.route("/data", methods=["GET"])
def get_insights_data():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    insights = get_insights_workflow(time_frame)
    return jsonify(insights)


@bp.route("/strategy", methods=["GET"])
def get_strategy():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"

    cached = get_cached("strategy", time_frame)
    if cached is not None:
        return jsonify(cached)
        
    dec_data = get_decision_intelligence_data(lightweight=True)
    categories_data = get_content_coverage_matrix()
    brands_data = get_brand_opportunity_data()
    intent_data = get_intent_opportunity_data()
    rec_perf = get_recommendation_performance_data()
    
    opps_payload = {
        "top_opportunities": dec_data["top_opportunities"],
        "categories_data": categories_data,
        "brands_data": brands_data,
        "intent_data": intent_data,
        "recommendation_performance": rec_perf
    }
    strategy = generate_content_strategy(opps_payload)
    set_cached("strategy", time_frame, strategy)
    return jsonify(strategy)


@bp.route("/assets", methods=["GET"])
def get_assets():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"

    cached = get_cached("assets", time_frame)
    if cached is not None:
        return jsonify(cached)
        
    strategy = get_cached("strategy", time_frame)
    if strategy is None:
        # Generate and cache strategy
        dec_data = get_decision_intelligence_data(lightweight=True)
        categories_data = get_content_coverage_matrix()
        brands_data = get_brand_opportunity_data()
        intent_data = get_intent_opportunity_data()
        rec_perf = get_recommendation_performance_data()
        
        opps_payload = {
            "top_opportunities": dec_data["top_opportunities"],
            "categories_data": categories_data,
            "brands_data": brands_data,
            "intent_data": intent_data,
            "recommendation_performance": rec_perf
        }
        strategy = generate_content_strategy(opps_payload)
        set_cached("strategy", time_frame, strategy)
        
    assets = map_content_strategy_to_assets(strategy)
    set_cached("assets", time_frame, assets)
    return jsonify(assets)


@bp.route("/publishing-plan", methods=["GET"])
def get_publishing_plan():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"

    cached = get_cached("publishing_plan", time_frame)
    if cached is not None:
        return jsonify(cached)
        
    assets = get_cached("assets", time_frame)
    if assets is None:
        # Generate strategy and assets first
        strategy = get_cached("strategy", time_frame)
        if strategy is None:
            dec_data = get_decision_intelligence_data(lightweight=True)
            categories_data = get_content_coverage_matrix()
            brands_data = get_brand_opportunity_data()
            intent_data = get_intent_opportunity_data()
            rec_perf = get_recommendation_performance_data()
            
            opps_payload = {
                "top_opportunities": dec_data["top_opportunities"],
                "categories_data": categories_data,
                "brands_data": brands_data,
                "intent_data": intent_data,
                "recommendation_performance": rec_perf
            }
            strategy = generate_content_strategy(opps_payload)
            set_cached("strategy", time_frame, strategy)
        assets = map_content_strategy_to_assets(strategy)
        set_cached("assets", time_frame, assets)
        
    plan = generate_content_publishing_plan(assets)
    set_cached("publishing_plan", time_frame, plan)
    return jsonify(plan)


@bp.route("/performance", methods=["GET"])
def get_performance():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"

    cached = get_cached("performance", time_frame)
    if cached is not None:
        return jsonify(cached)
        
    performance = evaluate_content_performance_feedback()
    set_cached("performance", time_frame, performance)
    return jsonify(performance)


@bp.route("/governance", methods=["GET"])
def get_governance():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"

    cached = get_cached("governance", time_frame)
    if cached is not None:
        return jsonify(cached)
        
    plan = get_cached("publishing_plan", time_frame)
    if plan is None:
        # Load / compute assets and strategy
        assets = get_cached("assets", time_frame)
        if assets is None:
            strategy = get_cached("strategy", time_frame)
            if strategy is None:
                dec_data = get_decision_intelligence_data(lightweight=True)
                categories_data = get_content_coverage_matrix()
                brands_data = get_brand_opportunity_data()
                intent_data = get_intent_opportunity_data()
                rec_perf = get_recommendation_performance_data()
                opps_payload = {
                    "top_opportunities": dec_data["top_opportunities"],
                    "categories_data": categories_data,
                    "brands_data": brands_data,
                    "intent_data": intent_data,
                    "recommendation_performance": rec_perf
                }
                strategy = generate_content_strategy(opps_payload)
                set_cached("strategy", time_frame, strategy)
            assets = map_content_strategy_to_assets(strategy)
            set_cached("assets", time_frame, assets)
        plan = generate_content_publishing_plan(assets)
        set_cached("publishing_plan", time_frame, plan)
        
    assets = get_cached("assets", time_frame)
    
    performance = get_cached("performance", time_frame)
    if performance is None:
        performance = evaluate_content_performance_feedback()
        set_cached("performance", time_frame, performance)
        
    execution_plan = generate_execution_plan(plan, assets, performance)
    governance = generate_execution_governance_layer(execution_plan, assets, performance)
    set_cached("governance", time_frame, governance)
    return jsonify(governance)


@bp.route("/recompute", methods=["GET", "POST"])
def trigger_recompute():
    layer = request.args.get("layer", "all")
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    invalidate_cache(layer, time_frame)
    
    if layer == "strategy":
        return get_strategy()
    elif layer == "assets":
        return get_assets()
    elif layer == "publishing-plan":
        return get_publishing_plan()
    elif layer == "performance":
        return get_performance()
    elif layer == "governance":
        return get_governance()
    elif layer == "all":
        # Recompute all sequentially
        get_strategy()
        get_assets()
        get_publishing_plan()
        get_performance()
        get_governance()
        return jsonify({
            "status": "recomputed_all",
            "time_frame": time_frame
        })
    else:
        return jsonify({"error": "Invalid layer specified"}), 400
