# app/admin/insights.py
import time
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
# from app.application.interaction.get_insights import get_insights_workflow
from app.domains.analytics import (
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


@bp.route("/widget/recommendations", methods=["GET"])
def widget_recommendations():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
    
    rec_perf = get_recommendation_performance_data()
    return render_template("admin/control_panel/insights/_summary_cards.html", metrics=rec_perf)


@bp.route("/widget/top-opportunities", methods=["GET"])
def widget_top_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    dec_data = get_decision_intelligence_data(lightweight=True)
    return render_template("admin/control_panel/insights/_top_opportunities_rows.html", items=dec_data.get("top_opportunities", []))


@bp.route("/widget/action-queue", methods=["GET"])
def widget_action_queue():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    dec_data = get_decision_intelligence_data(lightweight=True)
    return render_template("admin/control_panel/insights/_action_queue_cards.html", items=dec_data.get("action_queue", []))


@bp.route("/widget/coverage-matrix", methods=["GET"])
def widget_coverage_matrix():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    coverage_matrix = get_content_coverage_matrix()
    return render_template("admin/control_panel/insights/_coverage_matrix_rows.html", items=coverage_matrix)


@bp.route("/widget/intent-opportunities", methods=["GET"])
def widget_intent_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    intent_opportunities = get_intent_opportunity_data()
    return render_template("admin/control_panel/insights/_intent_opportunities_cards.html", items=intent_opportunities)


@bp.route("/widget/brand-opportunities", methods=["GET"])
def widget_brand_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    brand_opportunities = get_brand_opportunity_data()
    return render_template("admin/control_panel/insights/_brand_opportunities_rows.html", items=brand_opportunities)


@bp.route("/widget/content-strategy", methods=["GET"])
def widget_content_strategy():
    time_frame = request.args.get("time_frame", "7_days")
    entity_filter = request.args.get("entity", "")
    
    cached = get_cached("strategy", time_frame)
    if cached is None:
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
        cached = generate_content_strategy(opps_payload)
        set_cached("strategy", time_frame, cached)

    items = cached
    if entity_filter:
        lower_filter = entity_filter.lower()
        items = [item for item in items if lower_filter in str(item.get("entity", "")).lower()]
        
    headers = {"X-Empty": "true"} if not items else {}
    return render_template("admin/control_panel/insights/_content_strategy_rows.html", items=items), 200, headers


@bp.route("/widget/asset-mapping", methods=["GET"])
def widget_asset_mapping():
    time_frame = request.args.get("time_frame", "7_days")
    entity_filter = request.args.get("entity", "")
    
    cached = get_cached("assets", time_frame)
    if cached is None:
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
        cached = map_content_strategy_to_assets(strategy)
        set_cached("assets", time_frame, cached)

    items = cached
    if entity_filter:
        lower_filter = entity_filter.lower()
        items = [item for item in items if lower_filter in str(item.get("entity", "")).lower()]
        
    headers = {"X-Empty": "true"} if not items else {}
    return render_template("admin/control_panel/insights/_asset_mapping_rows.html", items=items), 200, headers


@bp.route("/widget/publishing-plan", methods=["GET"])
def widget_publishing_plan():
    time_frame = request.args.get("time_frame", "7_days")
    entity_filter = request.args.get("entity", "")
    
    cached = get_cached("publishing_plan", time_frame)
    if cached is None:
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
        cached = generate_content_publishing_plan(assets)
        set_cached("publishing_plan", time_frame, cached)

    weekly_plan = []
    for week in cached.get("weekly_plan", []):
        tasks = week.get("tasks", [])
        if entity_filter:
            lower_filter = entity_filter.lower()
            tasks = [t for t in tasks if lower_filter in str(t.get("entity", "")).lower()]
        weekly_plan.append({
            "week": week.get("week"),
            "tasks": tasks
        })
        
    total_tasks = sum(len(w["tasks"]) for w in weekly_plan)
    platform_counts = {"youtube": 0, "pinterest": 0, "blog": 0}
    action_counts = {"reuse": 0, "update": 0, "create": 0, "postpone": 0}
    for week in weekly_plan:
        for t in week["tasks"]:
            p = t.get("platform")
            a = t.get("action")
            if p in platform_counts:
                platform_counts[p] += 1
            if a in action_counts:
                action_counts[a] += 1
                
    headers = {"X-Empty": "true"} if total_tasks == 0 else {}
    return render_template(
        "admin/control_panel/insights/_publishing_plan_grid.html",
        weekly_plan=weekly_plan,
        total_tasks=total_tasks,
        platform_counts=platform_counts,
        action_counts=action_counts
    ), 200, headers


@bp.route("/widget/performance-feedback", methods=["GET"])
def widget_performance_feedback():
    time_frame = request.args.get("time_frame", "7_days")
    entity_filter = request.args.get("entity", "")
    
    cached = get_cached("performance", time_frame)
    if cached is None:
        cached = evaluate_content_performance_feedback()
        set_cached("performance", time_frame, cached)

    eval_results = cached.get("evaluation_results", [])
    failures = cached.get("failures_detected", [])
    
    if entity_filter:
        lower_filter = entity_filter.lower()
        eval_results = [item for item in eval_results if lower_filter in str(item.get("entity", "")).lower()]
        failures = [
            f for f in failures
            if lower_filter in str(f.get("entity", "")).lower() or lower_filter in str(f.get("title", "")).lower()
        ]
        
    headers = {"X-Empty": "true"} if not eval_results else {}
    return render_template(
        "admin/control_panel/insights/_performance_feedback_inner.html",
        average_accuracy=cached.get("average_accuracy", 0.0),
        evaluation_results=eval_results,
        failures_detected=failures
    ), 200, headers


@bp.route("/widget/autonomous-execution", methods=["GET"])
def widget_autonomous_execution():
    time_frame = request.args.get("time_frame", "7_days")
    
    cached = get_cached("governance", time_frame)
    if cached is None:
        plan = get_cached("publishing_plan", time_frame)
        if plan is None:
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
        cached = generate_execution_governance_layer(execution_plan, assets, performance)
        set_cached("governance", time_frame, cached)

    execution_plan = cached.get("execution_plan", {})
    auto_execute = execution_plan.get("auto_execute", [])
    needs_review = execution_plan.get("needs_review", [])
    blocked = execution_plan.get("blocked", [])
    is_empty = len(auto_execute) == 0 and len(needs_review) == 0 and len(blocked) == 0
    headers = {"X-Empty": "true"} if is_empty else {}
    return render_template(
        "admin/control_panel/insights/_autonomous_execution_grid.html",
        auto_execute=auto_execute,
        needs_review=needs_review,
        blocked=blocked
    ), 200, headers


@bp.route("/widget/governance", methods=["GET"])
def widget_governance():
    time_frame = request.args.get("time_frame", "7_days")
    
    cached = get_cached("governance", time_frame)
    if cached is None:
        plan = get_cached("publishing_plan", time_frame)
        if plan is None:
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
        cached = generate_execution_governance_layer(execution_plan, assets, performance)
        set_cached("governance", time_frame, cached)
        
    queued_tasks = cached.get("queued_tasks", [])
    approved_tasks = cached.get("approved_tasks", [])
    blocked_tasks = cached.get("blocked_tasks", [])
    is_empty = len(queued_tasks) == 0 and len(approved_tasks) == 0 and len(blocked_tasks) == 0
    headers = {"X-Empty": "true"} if is_empty else {}
    return render_template(
        "admin/control_panel/insights/_governance_grid.html",
        mode=cached.get("mode", ""),
        queued_tasks=queued_tasks,
        approved_tasks=approved_tasks,
        blocked_tasks=blocked_tasks
    ), 200, headers



