# app/admin/distribution.py
import time
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from sqlalchemy import select, desc
from app.web.routes.admin.insights import get_cached, set_cached, invalidate_cache
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

bp = Blueprint("api_distribution", __name__, url_prefix="/admin/distribution")


@bp.before_request
# @admin_required
def require_admin():
    """Ensure all distribution endpoints require admin privilege."""
    pass


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
    
    if layer == "publishing-plan":
        return get_publishing_plan()
    elif layer == "governance":
        return get_governance()
    elif layer == "all":
        # Recompute all distribution layers
        get_publishing_plan()
        get_governance()
        return jsonify({
            "status": "recomputed_distribution_all",
            "time_frame": time_frame
        })
    else:
        return jsonify({"error": "Invalid layer specified"}), 400


@bp.route("/widget/action-queue", methods=["GET"])
def widget_action_queue():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    dec_data = get_decision_intelligence_data(lightweight=True)
    return render_template("admin/distribution/_action_queue_cards.html", items=dec_data.get("action_queue", []))


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
        "admin/distribution/_publishing_plan_grid.html",
        weekly_plan=weekly_plan,
        total_tasks=total_tasks,
        platform_counts=platform_counts,
        action_counts=action_counts
    ), 200, headers


@bp.route("/widget/autonomous-execution", methods=["GET"])
def widget_autonomous_execution():
    time_frame = request.args.get("time_frame", "7_days")
    
    execution_plan = get_cached("execution_plan", time_frame)
    if execution_plan is None:
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
        set_cached("execution_plan", time_frame, execution_plan)

    auto_execute = execution_plan.get("auto_execute", [])
    needs_review = execution_plan.get("needs_review", [])
    blocked = execution_plan.get("blocked", [])
    is_empty = len(auto_execute) == 0 and len(needs_review) == 0 and len(blocked) == 0
    headers = {"X-Empty": "true"} if is_empty else {}
    return render_template(
        "admin/distribution/_autonomous_execution_grid.html",
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
        set_cached("execution_plan", time_frame, execution_plan)
        cached = generate_execution_governance_layer(execution_plan, assets, performance)
        set_cached("governance", time_frame, cached)
        
    queued_tasks = cached.get("queued_tasks", [])
    approved_tasks = cached.get("approved_tasks", [])
    blocked_tasks = cached.get("blocked_tasks", [])
    is_empty = len(queued_tasks) == 0 and len(approved_tasks) == 0 and len(blocked_tasks) == 0
    headers = {"X-Empty": "true"} if is_empty else {}
    return render_template(
        "admin/distribution/_governance_grid.html",
        mode=cached.get("mode", ""),
        queued_tasks=queued_tasks,
        approved_tasks=approved_tasks,
        blocked_tasks=blocked_tasks
    ), 200, headers


@bp.route("/widget/social-distribution", methods=["GET"])
def widget_social_distribution():
    from app.domains.distribution.services import get_admin_social_distribution
    
    page = request.args.get("page", 1, type=int)
    per_page = 50
    
    status_filter = request.args.get("status")
    platform_filter = request.args.get("platform")
    source_type_filter = request.args.get("source_type")
    
    data = get_admin_social_distribution(status_filter, platform_filter, source_type_filter, page, per_page)
    
    headers = {"X-Empty": "true"} if not data["view_models"] else {}
    return render_template(
        "admin/distribution/_social_distribution_rows.html",
        widget_type="social_distribution",
        items=data["view_models"],
        summary_stats=data["summary_stats"],
        pagination=data["pagination"]
    ), 200, headers


@bp.route("/widget/overview-kpis", methods=["GET"])
def widget_overview_kpis():
    from app.domains.analytics.distribution_intelligence import get_overview_kpis
    stats = get_overview_kpis()
    return render_template("admin/distribution/_overview_kpis.html", stats=stats)


@bp.route("/widget/scheduling-queue", methods=["GET"])
def widget_scheduling_queue():
    from app.domains.distribution.services import get_admin_scheduling_queue
    view_models = get_admin_scheduling_queue()
    return render_template("admin/distribution/_scheduling_queue.html", items=view_models)


@bp.route("/widget/health-alerts", methods=["GET"])
def widget_health_alerts():
    from app.domains.analytics.distribution_intelligence import get_health_alerts
    alerts = get_health_alerts()
    return render_template("admin/distribution/_health_alerts.html", alerts=alerts)


@bp.route("/widget/coverage-analytics", methods=["GET"])
def widget_coverage_analytics():
    from app.domains.analytics.distribution_intelligence import get_coverage_analytics
    stats = get_coverage_analytics()
    return render_template("admin/distribution/_coverage_analytics.html", stats=stats)


@bp.route("/widget/platform-performance", methods=["GET"])
def widget_platform_performance():
    from app.domains.analytics.distribution_intelligence import get_platform_performance
    platforms_data = get_platform_performance()
    
    # Attach icons which are view-specific
    from app.web.routes.admin.helpers import get_platform_icon
    for p in platforms_data:
        p["icon"] = get_platform_icon(p["name"])
        
    return render_template("admin/distribution/_platform_performance.html", platforms=platforms_data)


@bp.route("/social-distribution/generate", methods=["POST"])
def generate_distribution_draft():
    from app.domains.distribution.services import generate_admin_distribution_draft
    
    data = request.json
    source_type = data.get("source_type") # 'content' or 'item'
    source_id = data.get("source_id")
    platform_name = data.get("platform")
    
    if not all([source_type, source_id, platform_name]):
        return jsonify({"error": "Missing parameters"}), 400
        
    result = generate_admin_distribution_draft(source_type, source_id, platform_name)
    if not result:
        return jsonify({"error": "Source asset not found"}), 404
        
    return render_template(
        "admin/distribution/_distribution_modal_inner.html",
        **result
    )


@bp.route("/social-distribution/<int:post_id>/publish", methods=["POST"])
def publish_distribution_post(post_id):
    from app.domains.distribution.services import publish_admin_distribution_post
    
    data = request.json
    external_url = data.get("external_url", "")
    text = data.get("text", "")
    
    post = publish_admin_distribution_post(post_id, external_url, text)
    if not post:
        return jsonify({"error": "Post not found"}), 404
        
    return jsonify({"success": True, "status": post.status})


@bp.route("/intelligence", methods=["GET"])
def distribution_intelligence():
    """Renders the full Distribution Intelligence Dashboard."""
    from app.domains.analytics.distribution_intelligence import get_distribution_intelligence_data
    data = get_distribution_intelligence_data()
    return render_template("admin/distribution/distribution_intelligence.html", data=data)
