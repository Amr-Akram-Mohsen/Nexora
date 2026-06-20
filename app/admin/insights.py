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
# @admin_required
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


def _prepare_recommendation_view_model(rec_perf):
    if not rec_perf:
        return None
        
    view_model = dict(rec_perf)
    
    if "quality_scores" in view_model:
        q_scores = view_model["quality_scores"]
        
        rec_types = []
        for rtype, rdata in q_scores.get("recommendation_types", {}).items():
            label = "Related Content" if rtype == "related_content" else "Related Products" if rtype == "related_product" else "Shop Products"
            rec_types.append({"type_id": rtype, "label": label, **rdata})
        q_scores["recommendation_types_list"] = rec_types
        
        page_types = []
        for ptype, pdata in q_scores.get("page_types", {}).items():
            label = "Content Pages" if ptype == "content" else "Product Pages"
            page_types.append({"type_id": ptype, "label": label, **pdata})
        q_scores["page_types_list"] = page_types
        
        categories = []
        for catName, cdata in q_scores.get("categories", {}).items():
            categories.append({"name": catName, **cdata})
        categories.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        q_scores["top_categories"] = categories[:3]
        
    if "diagnoses" in view_model:
        diagnoses_list = []
        for rtype, ddata in view_model["diagnoses"].items():
            label = "Related Content" if rtype == "related_content" else "Related Products" if rtype == "related_product" else "Shop Products"
            badge_class = "badge-success" if ddata.get("classification") == "High" else "badge-warning" if ddata.get("classification") == "Medium" else "badge-danger"
            rtype_class = "product" if rtype == "related_product" else "shop" if rtype == "shop_product" else "content"
            diagnoses_list.append({
                "type_id": rtype,
                "label": label,
                "badge_class": badge_class,
                "rtype_class": rtype_class,
                **ddata
            })
        view_model["diagnoses_list"] = diagnoses_list
        
    return view_model


@bp.route("/widget/recommendations", methods=["GET"])
def widget_recommendations():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
    
    rec_perf = get_recommendation_performance_data()
    view_model = _prepare_recommendation_view_model(rec_perf)
    return render_template("admin/control_panel/insights/_summary_cards.html", metrics=view_model)


@bp.route("/widget/top-opportunities", methods=["GET"])
def widget_top_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    dec_data = get_decision_intelligence_data(lightweight=True)
    return render_template("admin/control_panel/insights/_insights_rows.html", widget_type="top_opportunities", items=dec_data.get("top_opportunities", []))


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
    return render_template("admin/control_panel/insights/_insights_rows.html", widget_type="coverage_matrix", items=coverage_matrix)


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
    return render_template("admin/control_panel/insights/_insights_rows.html", widget_type="brand_opportunities", items=brand_opportunities)


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
    return render_template("admin/control_panel/insights/_insights_rows.html", widget_type="content_strategy", items=items), 200, headers


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
    return render_template("admin/control_panel/insights/_insights_rows.html", widget_type="asset_mapping", items=items), 200, headers


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
    from app.admin.tables import INSIGHTS_TABLES
    return render_template(
        "admin/control_panel/insights/_performance_feedback_inner.html",
        average_accuracy=cached.get("average_accuracy", 0.0),
        evaluation_results=eval_results,
        failures_detected=failures,
        tables=INSIGHTS_TABLES
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
        set_cached("execution_plan", time_frame, execution_plan)
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


@bp.route("/widget/social-distribution", methods=["GET"])
def widget_social_distribution():
    from app.domains.distribution.models import DistributionPost, DistributionPlatform
    from sqlalchemy import select, desc
    from app.core.extensions import db
    
    posts = db.session.execute(
        select(DistributionPost, DistributionPlatform.name.label("platform_name"))
        .join(DistributionPlatform)
        .order_by(desc(DistributionPost.created_at))
        .limit(50)
    ).all()
    
    view_models = []
    for post, p_name in posts:
        source_title = "Unknown"
        if post.source:
            source_title = getattr(post.source, "title", getattr(post.source, "name", f"ID: {post.source_target_id}"))
            
        view_models.append({
            "id": post.id,
            "platform": p_name,
            "source_title": source_title,
            "source_type": post.source_target_type,
            "source_id": post.source_target_id,
            "status": post.status,
            "publish_date": post.publish_date.strftime("%Y-%m-%d %H:%M") if post.publish_date else "-",
            "views": post.views_count,
            "likes": post.likes_count,
            "clicks": post.clicks_count
        })
        
    headers = {"X-Empty": "true"} if not view_models else {}
    return render_template(
        "admin/control_panel/insights/_insights_rows.html",
        widget_type="social_distribution",
        items=view_models
    ), 200, headers


@bp.route("/social-distribution/generate", methods=["POST"])
def generate_distribution_draft():
    from app.domains.distribution.services import generate_social_post_template
    from app.domains.distribution.models import DistributionPost, DistributionPlatform
    from app.domains.content.models import Content
    from app.domains.item.models import Item
    from sqlalchemy import select
    from app.core.extensions import db
    
    data = request.json
    source_type = data.get("source_type") # 'content' or 'item'
    source_id = data.get("source_id")
    platform_name = data.get("platform")
    
    if not all([source_type, source_id, platform_name]):
        return jsonify({"error": "Missing parameters"}), 400
        
    # Get platform
    platform = db.session.execute(select(DistributionPlatform).filter_by(name=platform_name)).scalar_one_or_none()
    if not platform:
        platform = DistributionPlatform(name=platform_name)
        db.session.add(platform)
        db.session.commit()
        
    # Get source asset
    asset = None
    if source_type == "content":
        asset = db.session.get(Content, source_id)
    elif source_type == "item":
        asset = db.session.get(Item, source_id)
        
    if not asset:
        return jsonify({"error": "Source asset not found"}), 404
        
    # Generate content
    generated = generate_social_post_template(asset, platform_name)
    
    # Create or update Draft
    post = db.session.execute(
        select(DistributionPost).filter_by(
            platform_id=platform.id, 
            source_target_type=source_type, 
            source_target_id=source_id
        )
    ).scalar_one_or_none()
    
    if not post:
        post = DistributionPost(
            platform_id=platform.id,
            source_target_type=source_type,
            source_target_id=source_id,
            status="draft",
            platform_specific_text=generated["suggested_text"]
        )
        db.session.add(post)
        db.session.commit()
        
    return render_template(
        "admin/control_panel/insights/_distribution_modal_inner.html",
        post_id=post.id,
        platform=platform_name,
        post_type=generated["post_type"],
        text=post.platform_specific_text,
        status=post.status
    )


@bp.route("/social-distribution/<int:post_id>/publish", methods=["POST"])
def publish_distribution_post(post_id):
    from app.domains.distribution.models import DistributionPost
    from app.core.extensions import db
    from datetime import datetime, timezone
    
    data = request.json
    external_url = data.get("external_url", "")
    text = data.get("text", "")
    
    post = db.session.get(DistributionPost, post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
        
    post.status = "published"
    post.publish_date = datetime.now(timezone.utc)
    post.external_url = external_url
    if text:
        post.platform_specific_text = text
        
    db.session.commit()
    return jsonify({"success": True, "status": post.status})
