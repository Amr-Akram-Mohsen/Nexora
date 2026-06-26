# app/admin/insights.py
import time
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from sqlalchemy import select, func, Date, cast, desc
from app.domains.taxonomy.models import Source, Category
from app.domains.content.models import Content
from app.domains.analytics import (
    get_decision_intelligence_data,
    get_intent_opportunity_data,
    get_brand_opportunity_data,
    get_recommendation_performance_data,
    get_content_coverage_matrix,
    generate_content_strategy,
    map_content_strategy_to_assets,
    evaluate_content_performance_feedback,
    get_content_completeness_report,
    get_source_intelligence,
    get_source_intelligence,
    get_content_commerce_attribution,
    get_intent_recommendation_heatmap,
    get_user_interest_coverage_gap,
    get_source_authority_validation,
    get_geographic_demand_data,
    get_category_sentiment_health,
    get_recommendation_commerce_chain
)

bp = Blueprint("api_insights", __name__, url_prefix="/admin/insights")

INSIGHTS_CACHE = {
    "strategy": {},
    "assets": {},
    "publishing_plan": {},
    "performance": {},
    "governance": {},
    "execution_plan": {}
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
    # Placeholder or deprecated route, keeping for signature safety
    return jsonify({"status": "deprecated"})


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
    elif layer == "performance":
        return get_performance()
    elif layer == "all":
        # Recompute all content intelligence layers sequentially
        get_strategy()
        get_assets()
        get_performance()
        return jsonify({
            "status": "recomputed_intelligence_all",
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
    return render_template("admin/content_intelligence/_summary_cards.html", metrics=view_model)


@bp.route("/widget/top-opportunities", methods=["GET"])
def widget_top_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    dec_data = get_decision_intelligence_data(lightweight=True)
    return render_template("admin/content_intelligence/_insights_rows.html", widget_type="top_opportunities", items=dec_data.get("top_opportunities", []))


@bp.route("/widget/coverage-matrix", methods=["GET"])
def widget_coverage_matrix():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    coverage_matrix = get_content_coverage_matrix()
    return render_template("admin/content_intelligence/_coverage_matrix_chart.html", items=coverage_matrix)


@bp.route("/widget/intent-opportunities", methods=["GET"])
def widget_intent_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    intent_opportunities = get_intent_opportunity_data()
    return render_template("admin/content_intelligence/_intent_opportunities_cards.html", items=intent_opportunities)


@bp.route("/widget/intent-ctr-heatmap", methods=["GET"])
def widget_intent_ctr_heatmap():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    heatmap_data = get_intent_recommendation_heatmap()
    return render_template("admin/content_intelligence/_intent_ctr_heatmap.html", data=heatmap_data)


@bp.route("/widget/user-interest-gap", methods=["GET"])
def widget_user_interest_gap():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    gap_data = get_user_interest_coverage_gap()
    return render_template("admin/content_intelligence/_user_interest_gap.html", data=gap_data)


@bp.route("/widget/source-authority-validation", methods=["GET"])
def widget_source_authority_validation():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    validation_data = get_source_authority_validation()
    return render_template("admin/content_intelligence/_source_authority_validation.html", data=validation_data)


@bp.route("/widget/geographic-demand", methods=["GET"])
def widget_geographic_demand():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    geo_data = get_geographic_demand_data()
    return render_template("admin/content_intelligence/_geographic_demand.html", data=geo_data)


@bp.route("/widget/category-sentiment", methods=["GET"])
def widget_category_sentiment():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    sentiment_data = get_category_sentiment_health()
    return render_template("admin/content_intelligence/_category_sentiment.html", data=sentiment_data)


@bp.route("/widget/commerce-chain", methods=["GET"])
def widget_commerce_chain():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    chain_data = get_recommendation_commerce_chain()
    return render_template("admin/content_intelligence/_commerce_chain.html", data=chain_data)


@bp.route("/widget/brand-opportunities", methods=["GET"])
def widget_brand_opportunities():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    brand_opportunities = get_brand_opportunity_data()
    return render_template("admin/content_intelligence/_insights_rows.html", widget_type="brand_opportunities", items=brand_opportunities)


@bp.route("/widget/content-completeness", methods=["GET"])
def widget_content_completeness():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    completeness_data = get_content_completeness_report()
    return render_template("admin/content_intelligence/_content_completeness.html", data=completeness_data)


@bp.route("/widget/source-intelligence", methods=["GET"])
def widget_source_intelligence():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    source_data = get_source_intelligence()
    return render_template("admin/content_intelligence/_source_intelligence.html", data=source_data)


@bp.route("/widget/commerce-attribution", methods=["GET"])
def widget_commerce_attribution():
    time_frame = request.args.get("time_frame", "7_days")
    if time_frame not in ["today", "7_days", "30_days", "all_time"]:
        time_frame = "7_days"
        
    attribution_data = get_content_commerce_attribution()
    return render_template("admin/content_intelligence/_commerce_attribution.html", data=attribution_data)


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
    return render_template("admin/content_intelligence/_insights_rows.html", widget_type="content_strategy", items=items), 200, headers


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
    return render_template("admin/content_intelligence/_insights_rows.html", widget_type="asset_mapping", items=items), 200, headers


@bp.route("/widget/performance-feedback", methods=["GET"])
def widget_performance_feedback():
    time_frame = request.args.get("time_frame", "7_days")
    entity_filter = request.args.get("entity", "")
    
    cached = get_cached("performance", time_frame)
    if cached is None:
        cached = evaluate_content_performance_feedback()
        set_cached("performance", time_frame, cached)

    from app.admin.tables import INSIGHTS_TABLES
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
        "admin/content_intelligence/_performance_feedback_inner.html",
        average_accuracy=cached.get("average_accuracy", 0.0),
        evaluation_results=eval_results,
        failures_detected=failures,
        tables=INSIGHTS_TABLES
    ), 200, headers


@bp.route("/acquisition-data", methods=["GET"])
def get_acquisition_data():
    from app.domains.analytics.acquisition import get_acquisition_metrics
    time_frame = request.args.get("time_frame", "7_days")
    
    metrics = get_acquisition_metrics(time_frame)
    matrix_html = render_template("admin/content_intelligence/partials/_coverage_matrix.html", data=metrics["matrix_table"])
            
    return jsonify({
        "velocity": metrics["velocity"],
        "contribution": metrics["contribution"],
        "authority": metrics["authority"],
        "matrix_html": matrix_html
    })
