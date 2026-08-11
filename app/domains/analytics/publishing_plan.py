# app/domains/interaction/service/insights/publishing_plan.py
from app.domains.analytics.content_opportunities import (
    get_intent_opportunity_data,
    get_content_decay
)
from app.domains.analytics.trends import (
    get_trending_categories_data,
    get_trending_brands_data
)
from app.domains.analytics.shared import select_primary_platform

def generate_content_publishing_plan(mapped_content_data):
    """
    Generates a structured daily publishing calendar scheduled across 30 days.
    
    Integrates point complexity thresholds (videos = 3.0, articles = 1.0, pins = 0.5),
    workload points ceiling constraints (max 6.0 points/week), category spacing to avoid
    3-day category overlaps, content decay prioritization, and momentum signals.
    """
    intent_opps = get_intent_opportunity_data()
    intent_map = {product["category_name"]: product for product in intent_opps}
    
    # 1. Fetch momentum & compute scheduling weights
    cat_trends = {t["name"].lower(): float(t["pct_change"]) for t in get_trending_categories_data()}
    brand_trends = {t["name"].lower(): float(t["pct_change"]) for t in get_trending_brands_data()}

    items_with_weights = []
    for product in mapped_content_data:
        entity = product["entity"]
        etype = product["type"]
        score = product["opportunity_score"]
        
        # Get category/brand momentum trend from preloaded maps
        if etype.lower() == "category":
            momentum = cat_trends.get(entity.lower(), 0.0)
        else:
            momentum = brand_trends.get(entity.lower(), 0.0)
        
        # Get content traffic decay for existing assets
        max_decay = 0.0
        for asset in product.get("existing_assets", []):
            if asset["id"].startswith("content_"):
                c_id = int(asset["id"].split("_")[1])
                decay = get_content_decay(c_id)
                max_decay = max(max_decay, decay)
                
        # Calculate composite score to prioritize scheduling
        # Traffic decay pulls update tasks early; brand momentum gives dynamic urgency
        composite_score = score * 100.0 + (momentum * 0.1) + (max_decay * 0.5)
        
        items_with_weights.append({
            "product": product,
            "momentum": momentum,
            "max_decay": max_decay,
            "composite_score": composite_score
        })
        
    # Sort products by composite score descending
    items_with_weights.sort(key=lambda x: x["composite_score"], reverse=True)
    
    # Platform point complexities
    PLATFORM_POINTS = {
        "youtube": 3.0,
        "blog": 1.0,
        "pinterest": 0.5
    }
    
    # Initialize daily calendar slots (Day 1 to 30)
    daily_schedule = {day: [] for day in range(1, 31)}
    
    # Workload point tracks per week: Max 6.0 points per week
    # Week 1: Days 1-7, Week 2: Days 8-14, Week 3: Days 15-21, Week 4: Days 22-30
    weekly_points = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    
    # Entity spacing tracking (prevent category/brand duplicate scheduling within 3 days)
    entity_last_day = {}
    
    for entry in items_with_weights:
        product = entry["product"]
        entity = product["entity"]
        etype = product["type"]
        score = product["opportunity_score"]
        max_decay = entry["max_decay"]
        
        # 2. Select primary platform based on intent matching
        intent_opt = ""
        if etype == "category" and entity in intent_map:
            intent_opt = intent_map[entity].get("opportunity", "").lower()
        elif etype == "brand":
            intent_opt = "review"
            
        platform = select_primary_platform(etype, intent_opt)
            
        points = PLATFORM_POINTS.get(platform, 1.0)
        
        # 3. Reuse vs Update vs Create decisions
        existing_assets = product.get("existing_assets", [])
        matching_asset = None
        for asset in existing_assets:
            if platform == "youtube" and asset["type"] == "video":
                matching_asset = asset
                break
            elif platform in ["blog", "pinterest"] and asset["type"] == "article":
                matching_asset = asset
                break
                
        # Check if already distributed
        recently_published = False
        if matching_asset:
            d_posts = matching_asset.get("distribution_posts", [])
            for dp in d_posts:
                if dp["platform"] == platform and dp["status"] in ["published", "scheduled"]:
                    recently_published = True
                    break

        if recently_published:
            action = "monitor"
            reason_str = f"Already distributed on {platform}. Monitor social performance."
            source = matching_asset["id"]
            content_type = f"Published {matching_asset['type'].replace('_', ' ').title()}"
            points = 0.0 # Doesn't take workload points
        elif max_decay > 15.0 and matching_asset:
            action = "update"
            reason_str = f"Critical traffic decay detected: views dropped by {max_decay}%. Update and refresh for search SEO."
            source = matching_asset["id"]
            content_type = f"Decayed {matching_asset['type'].replace('_', ' ').title()}"
        elif matching_asset:
            action = matching_asset["action"]
            reason_str = f"Existing asset ({matching_asset['title']}) matches the strategy. Update or reuse."
            source = matching_asset["id"]
            content_type = f"Existing {matching_asset['type'].replace('_', ' ').title()}"
        else:
            action = "create"
            reason_str = f"No existing assets on {platform}. Create new {platform} content."
            source = "new"
            content_type = "New Video" if platform == "youtube" else ("New Infographic" if platform == "pinterest" else "New Article")
            
        # 4. Search earliest scheduling day slot fitting point limits and 3-day entity spacing constraints
        start_day = 1
        if max_decay > 15.0:
            # Decay tasks should start Day 1-3
            start_day = 1
        elif score < 0.45:
            # Low opportunity products go directly to backlog / Weeks 3-4 (Day 15+)
            start_day = 15
            
        scheduled_day = None
        for day in range(start_day, 31):
            # Spreading constraint: Max 1 task per day
            if len(daily_schedule[day]) >= 1:
                continue

            # Check 3-day spacing constraint
            last_day = entity_last_day.get(entity, -99)
            if day <= last_day + 2:
                continue
                
            # Check point complexity constraints per week
            week = 1 if day <= 7 else (2 if day <= 14 else (3 if day <= 21 else 4))
            if weekly_points[week] + points > 6.0:
                continue
                
            scheduled_day = day
            break
            
        # Fallback to backlog days
        if not scheduled_day:
            scheduled_day = 30
            
        # Save tracks
        week = 1 if scheduled_day <= 7 else (2 if scheduled_day <= 14 else (3 if scheduled_day <= 21 else 4))
        weekly_points[week] += points
        entity_last_day[entity] = scheduled_day
        
        # 5. Output Enhancements (Hook & SEO Optimization)
        if platform == "youtube":
            title_hook = f"📺 Hook: 'I Tested Every {entity} Brand So You Don't Have To!'"
        elif platform == "pinterest":
            title_hook = f"📌 Visual specs: 'INFOGRAPHIC: Ultimate {entity} Cheat Sheet'"
        else:
            title_hook = f"📝 SEO Guide: 'Best {entity} in Saudi Arabia: 2026 Buying Guide'"
            
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_of_week = day_names[(scheduled_day - 1) % 7]
        
        daily_schedule[scheduled_day].append({
            "entity": f"Day {scheduled_day} ({day_of_week}): {entity}",
            "action": action,
            "platform": platform,
            "content_type": content_type,
            "source": source,
            "priority": "high" if score >= 0.70 else ("medium" if score >= 0.45 else "low"),
            "reason": f"{title_hook} | {reason_str} | Momentum: {entry['momentum']}%"
        })

    # 6. Restructure daily slots back into Week 1, Week 2, and Backlog
    weekly_plan = [
        {"week": "Week 1", "tasks": []},
        {"week": "Week 2", "tasks": []},
        {"week": "Backlog", "tasks": []}
    ]
    
    for day, tasks in daily_schedule.items():
        if day <= 7:
            weekly_plan[0]["tasks"].extend(tasks)
        elif day <= 14:
            weekly_plan[1]["tasks"].extend(tasks)
        else:
            weekly_plan[2]["tasks"].extend(tasks)
            
    # Sort tasks in each column to render chronologically by day

    def get_task_day(task):
        try:
            return int(task["entity"].split(" ")[1])
        except (ValueError, IndexError):
            return 99
            
    for col in weekly_plan:
        col["tasks"].sort(key=get_task_day)
            
    return {"weekly_plan": weekly_plan}

