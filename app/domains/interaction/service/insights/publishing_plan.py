# app/domains/interaction/service/insights/publishing_plan.py
from app.domains.interaction.service.insights.opportunities import get_intent_opportunity_data

def generate_content_publishing_plan(mapped_content_data):
    """
    Generates a structured weekly publishing calendar by scheduling tasks
    for each opportunity entity based on priority, intent, and platform balance.
    """
    intent_opps = get_intent_opportunity_data()
    intent_map = {item["category_name"]: item for item in intent_opps}
    
    # Buckets for each timing/week
    weekly_buckets = {
        "Week 1": [], # High priority (score >= 0.75)
        "Week 2": [], # Medium priority (0.45 <= score < 0.75)
        "Backlog": [] # Low priority (score < 0.45)
    }
    
    # Sort items by opportunity score descending to process higher opportunities first
    sorted_items = sorted(mapped_content_data, key=lambda x: x["opportunity_score"], reverse=True)
    
    # Keep track of scheduled entities to avoid duplicate conflicts
    scheduled_entities = set()
    
    for item in sorted_items:
        entity = item["entity"]
        if entity in scheduled_entities:
            continue
        scheduled_entities.add(entity)
        
        score = item["opportunity_score"]
        
        # Priority rules
        if score >= 0.75:
            priority = "high"
            week_key = "Week 1"
        elif score >= 0.45:
            priority = "medium"
            week_key = "Week 2"
        else:
            priority = "low"
            week_key = "Backlog"
            
        weekly_buckets[week_key].append((item, priority))
        
    # Compile final tasks per week
    weekly_plan = [
        {"week": "Week 1", "tasks": []},
        {"week": "Week 2", "tasks": []},
        {"week": "Backlog", "tasks": []}
    ]
    
    # We will balance platforms within each week bucket
    for week_data in weekly_plan:
        week_name = week_data["week"]
        bucket_items = weekly_buckets[week_name]
        
        # Track platform counts within this week
        platform_counts = {"youtube": 0, "pinterest": 0, "blog": 0}
        
        # Sort items inside the bucket by score descending
        bucket_items.sort(key=lambda x: x[0]["opportunity_score"], reverse=True)
        
        for item, priority in bucket_items:
            entity = item["entity"]
            etype = item["type"]
            score = item["opportunity_score"]
            
            # Determine intent text
            intent_opt = ""
            if etype == "category" and entity in intent_map:
                intent_opt = intent_map[entity].get("opportunity", "").lower()
            elif etype == "brand":
                intent_opt = "review"
                
            # Platform rules with balancing
            scores = {}
            for p in ["youtube", "pinterest", "blog"]:
                base_affinity = 1.0
                
                # Check priority rules
                if p == "youtube" and ("comparison" in intent_opt or "vs" in entity.lower()):
                    base_affinity = 3.0
                elif p == "pinterest" and any(x in intent_opt for x in ["infographic", "checklist", "gift-ideas", "top-list", "tutorial"]):
                    base_affinity = 3.0
                elif p == "blog" and any(x in intent_opt for x in ["buying-guide", "buying guide", "review", "seo"]):
                    base_affinity = 3.0
                    
                # Adjust with negative penalty for over-scheduled platforms to balance
                scores[p] = base_affinity - (0.5 * platform_counts[p])
                
            platform = max(scores, key=scores.get)
            platform_counts[platform] += 1
            
            # Determine Action, content_type, and source
            # Action options: reuse | update | create | postpone
            existing_assets = item.get("existing_assets", [])
            
            # Find matching database asset
            matching_asset = None
            for asset in existing_assets:
                if platform == "youtube" and asset["type"] == "video":
                    matching_asset = asset
                    break
                elif platform == "blog" and asset["type"] == "article":
                    matching_asset = asset
                    break
                elif platform == "pinterest" and asset["type"] == "article":
                    matching_asset = asset
                    break
                    
            if priority == "low":
                action = "postpone"
                source = "new" if not matching_asset else matching_asset["id"]
                reason = f"Postponed due to low opportunity score ({score:.2f})."
                content_type = "Backlog Item"
            else:
                if matching_asset:
                    if matching_asset["action"] == "reuse":
                        action = "reuse"
                        reason = f"High relevance matching database asset found. Reuse {matching_asset['title']}."
                    else:
                        action = "update"
                        reason = f"Existing asset {matching_asset['title']} needs updates for freshness."
                    source = matching_asset["id"]
                    content_type = f"Existing {matching_asset['type'].replace('_', ' ').title()}"
                else:
                    action = "create"
                    source = "new"
                    reason = f"No existing asset found for {platform}. Create new {platform} content."
                    content_type = "New Video" if platform == "youtube" else ("New Infographic" if platform == "pinterest" else "New Article")
                    
            week_data["tasks"].append({
                "entity": entity,
                "action": action,
                "platform": platform,
                "content_type": content_type,
                "source": source,
                "priority": priority,
                "reason": reason
            })
            
    return {"weekly_plan": weekly_plan}
