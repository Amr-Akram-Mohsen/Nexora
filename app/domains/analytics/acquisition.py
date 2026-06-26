from sqlalchemy import func, select, cast, Date, desc
from app.core.extensions import db
from app.domains.taxonomy.models import Source, Category
from app.domains.content.models import Content


def get_acquisition_metrics(time_frame="7_days"):
    """
    Computes acquisition velocity, source contribution, 
    authority distribution, and category coverage matrix.
    Returns plain dictionaries.
    """
    # 1. Content Acquisition Velocity (top 5 sources)
    top_sources = db.session.execute(
        select(Source.id, Source.name)
        .join(Content, Content.source_id == Source.id)
        .group_by(Source.id, Source.name)
        .order_by(desc(func.count(Content.id)))
        .limit(5)
    ).all()
    
    top_source_ids = [s.id for s in top_sources]
    source_names = {s.id: s.name for s in top_sources}
    
    velocity_data = {}
    if top_source_ids:
        rows = db.session.execute(
            select(Content.source_id, cast(Content.ingested_at, Date).label('day'), func.count(Content.id))
            .where(Content.source_id.in_(top_source_ids))
            .group_by(Content.source_id, cast(Content.ingested_at, Date))
            .order_by(cast(Content.ingested_at, Date))
        ).all()
        for src_id, day, count in rows:
            day_str = day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)
            s_name = source_names[src_id]
            if s_name not in velocity_data:
                velocity_data[s_name] = {}
            velocity_data[s_name][day_str] = count

    all_dates = set()
    for s_name, data in velocity_data.items():
        all_dates.update(data.keys())
    all_dates = sorted(list(all_dates))[-30:]
    
    datasets = []
    for s_name, data in velocity_data.items():
        datasets.append({
            "label": s_name,
            "data": [data.get(d, 0) for d in all_dates]
        })
        
    velocity = {
        "labels": all_dates,
        "datasets": datasets
    }
    
    # 2. Source Contribution Analysis (Pie chart)
    contribution_rows = db.session.execute(
        select(Source.name, func.count(Content.id))
        .join(Content, Content.source_id == Source.id)
        .group_by(Source.id, Source.name)
        .order_by(desc(func.count(Content.id)))
        .limit(10)
    ).all()
    contribution = {
        "labels": [r[0] for r in contribution_rows],
        "data": [r[1] for r in contribution_rows]
    }
    
    # 3. Authority Distribution (Histogram)
    authority_rows = db.session.execute(
        select(Source.authority_score, func.count(Source.id))
        .group_by(Source.authority_score)
    ).all()
    buckets = {f"{i}-{i+9}": 0 for i in range(0, 100, 10)}
    for score, count in authority_rows:
        if score is None: continue
        score_int = int(score)
        bucket_idx = (score_int // 10) * 10
        bucket_idx = min(90, bucket_idx)
        buckets[f"{bucket_idx}-{bucket_idx+9}"] += count
    
    authority = {
        "labels": list(buckets.keys()),
        "data": list(buckets.values())
    }
    
    # 4. Category x Source Coverage Matrix
    matrix_table = {"sources": [], "rows": []}
    if top_source_ids:
        matrix_rows = db.session.execute(
            select(Category.name, Source.name, func.count(Content.id))
            .join(Content, Content.category_id == Category.id)
            .join(Source, Content.source_id == Source.id)
            .where(Source.id.in_(top_source_ids))
            .group_by(Category.name, Source.name)
        ).all()
        
        matrix = {}
        for cat_name, src_name, count in matrix_rows:
            if cat_name not in matrix:
                matrix[cat_name] = {}
            matrix[cat_name][src_name] = count
            
        matrix_table["sources"] = [source_names[sid] for sid in top_source_ids]
        for cat_name, sources_dict in matrix.items():
            row = {"category": cat_name, "counts": {}}
            for s_name in matrix_table["sources"]:
                row["counts"][s_name] = sources_dict.get(s_name, 0)
            matrix_table["rows"].append(row)
            
    return {
        "velocity": velocity,
        "contribution": contribution,
        "authority": authority,
        "matrix_table": matrix_table
    }
