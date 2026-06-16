# app/domains/interaction/service/insights/shared.py
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, case

def get_start_date(time_frame: str):
    now = datetime.now(timezone.utc)
    if time_frame == "today":
        return now - timedelta(days=1)
    elif time_frame == "7_days":
        return now - timedelta(days=7)
    elif time_frame == "30_days":
        return now - timedelta(days=30)
    else: # all_time
        return None

def score_opportunity_entity(
    demand_val: float, max_demand: float,
    content_val: float, max_content: float,
    avg_eng: float, max_avg_eng: float,
    perf_feedback: float,
    *,
    demand_w: float = 0.4,
    gap_w:    float = 0.4,
    eng_w:    float = 0.2,
    feedback_w: float = 0.3,
) -> float:
    norm_demand  = demand_val  / max_demand   if max_demand  > 0 else 0.0
    norm_gap     = 1.0 - (content_val / max_content if max_content > 0 else 0.0)
    norm_eng     = avg_eng     / max_avg_eng  if max_avg_eng > 0 else 0.0
    base_score   = demand_w * norm_demand + gap_w * norm_gap + eng_w * norm_eng
    score        = (1 - feedback_w) * base_score + feedback_w * perf_feedback
    return round(max(0.0, min(1.0, score)), 2)

def finalize_trend_stats(stats_dict: dict, id_key="id", name_key="name", slug_key="slug") -> list:
    """Convert accumulated {id: {period_a, period_b, ...}} to sorted trend result list."""
    results = []
    for stat in stats_dict.values():
        a, b = stat["period_a"], stat["period_b"]
        results.append({
            "id": stat[id_key], "name": stat[name_key], "slug": stat.get(slug_key),
            "period_a": a, "period_b": b,
            "change": a - b,
            "pct_change": round(((a - b) / b * 100.0) if b > 0 else (100.0 if a > 0 else 0.0), 1)
        })
    results.sort(key=lambda x: (x["period_a"], x["change"]), reverse=True)
    return results

def build_period_split_query(join_col, group_col, interaction_model, start_a, start_b):
    """Build the standard period-A vs period-B count query for an interaction type."""
    return select(
        group_col,
        func.count(case((interaction_model.created_at >= start_a, interaction_model.id))).label("a"),
        func.count(case(((interaction_model.created_at >= start_b) & (interaction_model.created_at < start_a), interaction_model.id))).label("b")
    ).join(interaction_model, join_col).group_by(group_col)

def compute_quality_scores(metrics: list, key_fn, *, ctr_key="ctr", imp_key="impressions", click_key="clicks") -> dict:
    """
    Compute normalized CTR × engagement_weight quality score for a metric list.
    key_fn: callable(item) -> dict key name.
    """
    max_ctr = max((m[ctr_key] for m in metrics), default=0.0)
    max_imp = max((m[imp_key] for m in metrics), default=0)
    scores = {}
    for m in metrics:
        norm_ctr = m[ctr_key] / max_ctr if max_ctr > 0 else 0.0
        eng_w    = m[imp_key] / max_imp if max_imp > 0 else 0.0
        scores[key_fn(m)] = {
            ctr_key:   m[ctr_key],
            imp_key:   m[imp_key],
            click_key: m[click_key],
            "quality_score": round(norm_ctr * eng_w, 2),
        }
    return scores

def select_primary_platform(entity_type: str, intent_opt: str) -> str:
    """Canonical platform selection from entity type and intent signal."""
    opt = (intent_opt or "").lower()
    if entity_type.lower() == "brand" or "comparison" in opt or "review" in opt:
        return "youtube"
    if "infographic" in opt or "checklist" in opt or "tutorial" in opt:
        return "pinterest"
    return "blog"
