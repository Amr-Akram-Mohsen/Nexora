from sqlalchemy import func, select, desc, case, cast, Integer
from functools import lru_cache
from app.core.extensions import db
from app.domains.interaction.models import View, Reaction, Comment, Save, ProductClick, RecommendationImpression, RecommendationClick
from app.domains.content.models import Content
from app.domains.product.models import Product, ProductStoreLink, ProductVariant
from app.domains.taxonomy.models import Category, Brand, Entity, IntentFacet
from app.domains.analytics.shared import (
    get_start_date,
    finalize_trend_stats,
    build_period_split_query,
    compute_quality_scores
)

def get_recommendation_performance_data():
    imp_rows = db.session.execute(
        select(RecommendationImpression.entity_type, func.count(RecommendationImpression.id))
        .group_by(RecommendationImpression.entity_type)
    ).all()
    imp_map = {r[0]: r[1] for r in imp_rows}

    clk_rows = db.session.execute(
        select(RecommendationClick.entity_type, func.count(RecommendationClick.id))
        .group_by(RecommendationClick.entity_type)
    ).all()
    clk_map = {r[0]: r[1] for r in clk_rows}

    related_content_impressions = imp_map.get("related_content", 0)
    related_products_impressions = imp_map.get("related_product", 0)
    shop_products_impressions = imp_map.get("shop_product", 0)

    related_content_clicks = clk_map.get("related_content", 0)
    related_products_clicks = clk_map.get("related_product", 0)
    shop_products_clicks = clk_map.get("shop_product", 0)

    related_content_ctr = round((related_content_clicks / related_content_impressions) * 100.0, 2) if related_content_impressions > 0 else 0.0
    related_products_ctr = round((related_products_clicks / related_products_impressions) * 100.0, 2) if related_products_impressions > 0 else 0.0
    shop_products_ctr = round((shop_products_clicks / shop_products_impressions) * 100.0, 2) if shop_products_impressions > 0 else 0.0

    total_impressions = related_content_impressions + related_products_impressions + shop_products_impressions
    total_clicks = related_content_clicks + related_products_clicks + shop_products_clicks
    overall_ctr = round((total_clicks / total_impressions) * 100.0, 2) if total_impressions > 0 else 0.0

    categories = db.session.execute(select(Category.id, Category.name)).all()
    cat_id_to_name = {cat.id: cat.name for cat in categories}
    
    cast_context_id = cast(RecommendationImpression.context_id, Integer)
    cast_context_id_click = cast(RecommendationClick.context_id, Integer)

    category_expr = case(
        (RecommendationImpression.entity_type == 'shop_product', Content.category_id),
        (RecommendationImpression.entity_type == 'related_product', Product.category_id),
        ((RecommendationImpression.entity_type == 'related_content') & (Content.category_id.isnot(None)), Content.category_id),
        else_=Product.category_id
    )

    click_category_expr = case(
        (RecommendationClick.entity_type == 'shop_product', Content.category_id),
        (RecommendationClick.entity_type == 'related_product', Product.category_id),
        ((RecommendationClick.entity_type == 'related_content') & (Content.category_id.isnot(None)), Content.category_id),
        else_=Product.category_id
    )

    category_stmt = select(
        category_expr,
        func.count(RecommendationImpression.id)
    ).outerjoin(Content, cast_context_id == Content.id)\
     .outerjoin(Product, cast_context_id == Product.id)\
     .group_by(category_expr)

    click_category_stmt = select(
        click_category_expr,
        func.count(RecommendationClick.id)
    ).outerjoin(Content, cast_context_id_click == Content.id)\
     .outerjoin(Product, cast_context_id_click == Product.id)\
     .group_by(click_category_expr)

    cat_stats = {cat_id: {"impressions": 0, "clicks": 0} for cat_id in cat_id_to_name.keys()}
    for cat_id, cnt in db.session.execute(category_stmt).all():
        if cat_id in cat_stats:
            cat_stats[cat_id]["impressions"] = cnt

    for cat_id, cnt in db.session.execute(click_category_stmt).all():
        if cat_id in cat_stats:
            cat_stats[cat_id]["clicks"] = cnt

    category_metrics = []
    for cat_id, name in cat_id_to_name.items():
        stats = cat_stats[cat_id]
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        category_metrics.append({
            "category_id": cat_id,
            "name": name,
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "ctr": round(ctr, 2)
        })

    page_type_expr = case(
        (RecommendationImpression.entity_type == 'shop_product', 'content'),
        (RecommendationImpression.entity_type == 'related_product', 'commercial'),
        ((RecommendationImpression.entity_type == 'related_content') & (Content.category_id.isnot(None)), 'content'),
        else_='commercial'
    )

    click_page_type_expr = case(
        (RecommendationClick.entity_type == 'shop_product', 'content'),
        (RecommendationClick.entity_type == 'related_product', 'commercial'),
        ((RecommendationClick.entity_type == 'related_content') & (Content.category_id.isnot(None)), 'content'),
        else_='commercial'
    )

    page_stmt = select(
        page_type_expr,
        func.count(RecommendationImpression.id)
    ).outerjoin(Content, cast_context_id == Content.id)\
     .outerjoin(Product, cast_context_id == Product.id)\
     .group_by(page_type_expr)

    click_page_stmt = select(
        click_page_type_expr,
        func.count(RecommendationClick.id)
    ).outerjoin(Content, cast_context_id_click == Content.id)\
     .outerjoin(Product, cast_context_id_click == Product.id)\
     .group_by(click_page_type_expr)

    page_stats = {
        "content": {"impressions": 0, "clicks": 0},
        "commercial": {"impressions": 0, "clicks": 0}
    }
    for ptype, cnt in db.session.execute(page_stmt).all():
        if ptype in page_stats:
            page_stats[ptype]["impressions"] = cnt

    for ptype, cnt in db.session.execute(click_page_stmt).all():
        if ptype in page_stats:
            page_stats[ptype]["clicks"] = cnt

    page_type_metrics = []
    for ptype in ["content", "commercial"]:
        stats = page_stats[ptype]
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        page_type_metrics.append({
            "page_type": ptype,
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "ctr": round(ctr, 2)
        })

    rectype_stats = {
        "related_content": {"impressions": related_content_impressions, "clicks": related_content_clicks},
        "related_product": {"impressions": related_products_impressions, "clicks": related_products_clicks},
        "shop_product": {"impressions": shop_products_impressions, "clicks": shop_products_clicks}
    }
    recommendation_type_metrics = []
    for rtype, stats in rectype_stats.items():
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        recommendation_type_metrics.append({
            "recommendation_type": rtype,
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "ctr": round(ctr, 2)
        })

    category_scores = compute_quality_scores(category_metrics, lambda c: c["name"])
    page_type_scores = compute_quality_scores(page_type_metrics, lambda p: p["page_type"])
    recommendation_type_scores = compute_quality_scores(recommendation_type_metrics, lambda r: r["recommendation_type"])

    diagnoses = {}
    for rtype in ["related_content", "related_product", "shop_product"]:
        stats = rectype_stats[rtype]
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        
        if ctr < 5.0:
            classification = "Low"
        elif ctr <= 15.0:
            classification = "Medium"
        else:
            classification = "High"
            
        q_score = recommendation_type_scores[rtype]["quality_score"]
        
        if rtype == "related_content":
            if classification == "Low":
                issue = "Low user interest in recommended articles"
                diagnosis = "Generic related article suggestions are failing to engage users."
                recommended_action = "Replace with comparison-focused articles or buying guides in the sidebar."
                expected_impact = "Boost reader click-through rate and session depth by matching user search intent."
                confidence = 0.80
            elif classification == "Medium":
                issue = "Moderate engagement on related articles"
                diagnosis = "Articles are relevant but could benefit from clearer call-to-actions."
                recommended_action = "Optimize sidebar article headlines and add clear teaser cards."
                expected_impact = "Improve content engagement and time-on-site metrics."
                confidence = 0.75
            else:
                issue = "High content recommendation affinity"
                diagnosis = "Users are highly receptive to related reading materials."
                recommended_action = "Expand related content slots and pin top-performing articles."
                expected_impact = "Further increase internal page-views and brand trust."
                confidence = 0.90
        elif rtype == "related_product":
            if classification == "Low":
                issue = "Low product suggestion clicks on product pages"
                diagnosis = "Recommended products do not align well with the main product."
                recommended_action = "Refine product-to-product similarity weights to favor same-category products."
                expected_impact = "Recover lost commercial intent on product detail pages."
                confidence = 0.85
            elif classification == "Medium":
                issue = "Moderate related product conversions"
                diagnosis = "Recommendations are functional but lack visual/promotional appeal."
                recommended_action = "Introduce promotional badges (e.g., 'Best Value', 'Trending') on cards."
                expected_impact = "Increase cross-sell volume and merchant referrals."
                confidence = 0.80
            else:
                issue = "High product cross-sell performance"
                diagnosis = "Alternative/complementary product selections are highly effective."
                recommended_action = "Increase product card density in content pages and sidebar grids."
                expected_impact = "Maximize revenue from high-performing commercial links."
                confidence = 0.95
        else: # shop_product
            if classification == "Low":
                issue = "Low commercial conversion of article reader base"
                diagnosis = "Article readers are ignoring the 'Shop Related Products' box."
                recommended_action = "Align shop recommendations strictly with products directly mentioned in content body."
                expected_impact = "Increase monetization efficiency of informational traffic."
                confidence = 0.75
            elif classification == "Medium":
                issue = "Moderate shop card click-through rate"
                diagnosis = "Offers are seen but price/merchant options could be more competitive."
                recommended_action = "Prioritize merchants with lowest prices and best ratings in the shop block."
                expected_impact = "Improve click-out rate to external affiliate stores."
                confidence = 0.85
            else:
                issue = "Exceptional article-to-shop transition rate"
                diagnosis = "Shop widgets are capturing user buying intent perfectly."
                recommended_action = "Prominently display the shop widget above the fold in high-traffic reviews."
                expected_impact = "Substantially scale affiliate click out and revenue."
                confidence = 0.90
                
        diagnoses[rtype] = {
            "ctr": round(ctr, 2),
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "classification": classification,
            "quality_score": q_score,
            "action_suggestion": {
                "issue": issue,
                "diagnosis": diagnosis,
                "recommended_action": recommended_action,
                "expected_impact": expected_impact,
                "confidence": confidence
            }
        }

    active_categories = [c for c in category_metrics if c["impressions"] > 0]
    if active_categories:
        avg_baseline = sum([c["ctr"] for c in active_categories]) / len(active_categories)
    else:
        avg_baseline = 0.0

    category_deviations = {}
    for c in category_metrics:
        if c["impressions"] > 0:
            category_deviations[c["name"]] = round(c["ctr"] - avg_baseline, 2)
        else:
            category_deviations[c["name"]] = 0.0

    if active_categories:
        best_cat = max(active_categories, key=lambda x: x["ctr"])
        worst_cat = min(active_categories, key=lambda x: x["ctr"])
        best_performing = {
            "name": best_cat["name"],
            "ctr": best_cat["ctr"],
            "deviation": category_deviations[best_cat["name"]]
        }
        worst_performing = {
            "name": worst_cat["name"],
            "ctr": worst_cat["ctr"],
            "deviation": category_deviations[worst_cat["name"]]
        }
    else:
        best_performing = {"name": "N/A", "ctr": 0.0, "deviation": 0.0}
        worst_performing = {"name": "N/A", "ctr": 0.0, "deviation": 0.0}

    benchmarking = {
        "best_category": best_performing,
        "worst_category": worst_performing,
        "average_baseline": round(avg_baseline, 2),
        "category_deviations": category_deviations
    }

    distinct_contexts = db.session.execute(
        select(func.count(func.distinct(RecommendationImpression.context_id)))
    ).scalar() or 0

    total_published_contents = db.session.execute(
        select(func.count(Content.id)).where(Content.is_published == True)
    ).scalar() or 1

    coverage_rate = round((distinct_contexts / total_published_contents) * 100.0, 2)

    return {
        "overall_ctr": overall_ctr,
        "related_products_ctr": related_products_ctr,
        "related_content_ctr": related_content_ctr,
        "shop_products_ctr": shop_products_ctr,
        "coverage_rate": coverage_rate,
        "impressions": {
            "related_content": related_content_impressions,
            "related_product": related_products_impressions,
            "shop_product": shop_products_impressions,
            "total": total_impressions
        },
        "clicks": {
            "related_content": related_content_clicks,
            "related_product": related_products_clicks,
            "shop_product": shop_products_clicks,
            "total": total_clicks
        },
        "diagnoses": diagnoses,
        "quality_scores": {
            "categories": category_scores,
            "page_types": page_type_scores,
            "recommendation_types": recommendation_type_scores
        },
        "benchmarking": benchmarking
    }

def get_intent_recommendation_heatmap():
    categories = db.session.execute(select(Category.id, Category.name)).all()
    intents = db.session.execute(select(IntentFacet.id, IntentFacet.name)).all()
    
    cat_map = {c.id: c.name for c in categories}
    intent_map = {i.id: i.name for i in intents}
    
    cast_context_id = cast(RecommendationImpression.context_id, Integer)
    cast_context_id_click = cast(RecommendationClick.context_id, Integer)
    
    imp_stmt = select(
        Content.category_id,
        Content.intent_id,
        func.count(RecommendationImpression.id)
    ).select_from(RecommendationImpression)\
     .join(Content, cast_context_id == Content.id)\
     .group_by(Content.category_id, Content.intent_id)
     
    clk_stmt = select(
        Content.category_id,
        Content.intent_id,
        func.count(RecommendationClick.id)
    ).select_from(RecommendationClick)\
     .join(Content, cast_context_id_click == Content.id)\
     .group_by(Content.category_id, Content.intent_id)
     
    heatmap = {}
    for cid in cat_map:
        heatmap[cid] = {iid: {"impressions": 0, "clicks": 0} for iid in intent_map}
        
    for cid, iid, cnt in db.session.execute(imp_stmt).all():
        if cid in heatmap and iid in heatmap[cid]:
            heatmap[cid][iid]["impressions"] = cnt
            
    for cid, iid, cnt in db.session.execute(clk_stmt).all():
        if cid in heatmap and iid in heatmap[cid]:
            heatmap[cid][iid]["clicks"] = cnt
            
    results = []
    for cid, name in cat_map.items():
        row = {"category_name": name, "intents": {}}
        for iid, iname in intent_map.items():
            imps = heatmap[cid][iid]["impressions"]
            clks = heatmap[cid][iid]["clicks"]
            ctr = (clks / imps * 100.0) if imps > 0 else None
            row["intents"][iname] = round(ctr, 1) if ctr is not None else None
        results.append(row)
        
    return {
        "intent_names": list(intent_map.values()),
        "heatmap": results
    }
