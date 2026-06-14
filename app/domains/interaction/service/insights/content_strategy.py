# app/domains/interaction/service/insights/content_strategy.py

def generate_content_strategy(opportunities_data):
    """
    Generates data-driven marketing content strategies (YouTube, Pinterest, Blog)
    based on opportunity scores, intent gaps, brand gaps, and CTR signals.
    """
    top_opps = opportunities_data.get("top_opportunities", [])
    categories_data = opportunities_data.get("categories_data", [])
    brands_data = opportunities_data.get("brands_data", [])
    intent_data = opportunities_data.get("intent_data", [])
    rec_perf = opportunities_data.get("recommendation_performance", {})
    
    # Quick lookup maps
    cat_map = {c["name"]: c for c in categories_data}
    brand_map = {b["name"]: b for b in brands_data}
    intent_map = {item["category_name"]: item for item in intent_data}
    
    # Related content CTR signal
    related_content_ctr = rec_perf.get("related_content_ctr", 0.0)
    prefer_comparisons = related_content_ctr < 5.0 # Low content CTR trigger
    
    strategies = []
    
    # Limit to top 5 opportunities
    for idx, opp in enumerate(top_opps[:5]):
        entity_name = opp["entity"]
        entity_type = opp["type"].lower() # "category" or "brand"
        score = opp["score"]
        
        youtube_ideas = []
        pinterest_ideas = []
        blog_ideas = []
        
        # Base templates for generating deterministic titles
        if entity_type == "category":
            cat_info = cat_map.get(entity_name, {})
            intent_info = intent_map.get(entity_name, {})
            gap_status = cat_info.get("gap_score", "Medium Gap")
            demand_lvl = cat_info.get("demand", "Medium")
            
            # YouTube Strategy
            if prefer_comparisons:
                youtube_ideas = [
                    f"Ultimate {entity_name} Comparison: Which One Should You Buy?",
                    f"Top 5 {entity_name} Face-Off & Performance Review"
                ]
            else:
                youtube_ideas = [
                    f"Complete {entity_name} Buying Guide: Don't Buy Until You Watch This!",
                    f"Top 10 Best {entity_name} of the Year: The Definitive List"
                ]
                
            # Pinterest Strategy
            pinterest_ideas = [
                f"How to Choose the Perfect {entity_name} (Infographic Guide)",
                f"The Ultimate {entity_name} Cheat Sheet & Specifications Comparison Checklist"
            ]
            
            # Blog Strategy
            intent_opt = intent_info.get("opportunity", "buying-guide") if intent_info else "buying-guide"
            if "comparison" in intent_opt.lower() or prefer_comparisons:
                blog_ideas = [
                    f"Direct Comparison: Head-to-Head {entity_name} Review",
                    f"Comprehensive Guide: What is the Best {entity_name} for Beginners?"
                ]
            elif "review" in intent_opt.lower():
                blog_ideas = [
                    f"In-Depth Review: Analyzing the Top-Rated {entity_name} in Saudi Arabia",
                    f"Why You Need a High-Quality {entity_name}: Honest Pros & Cons"
                ]
            else:
                blog_ideas = [
                    f"The Ultimate {entity_name} Buying Guide & Expert Recommendations",
                    f"5 Critical Features to Look for in a Modern {entity_name}"
                ]
                
            reason = f"High priority Category with {demand_lvl} demand and {gap_status.lower()}."
            
        else: # Brand opportunity
            brand_info = brand_map.get(entity_name, {})
            eng_level = brand_info.get("engagement_level", "Medium")
            
            # YouTube Strategy
            if prefer_comparisons:
                youtube_ideas = [
                    f"{entity_name} vs The Competition: Is It Worth the Premium Price?",
                    f"Testing {entity_name} Products: Honest Comparison & Review"
                ]
            else:
                youtube_ideas = [
                    f"The Complete Guide to {entity_name} Products: Features & Setup",
                    f"Unboxing & First Look: Newest Releases from {entity_name}"
                ]
                
            # Pinterest Strategy
            pinterest_ideas = [
                f"Visual Guide: Evolution of {entity_name} Top Models",
                f"{entity_name} Product Selection Cheat Sheet (Infographic)"
            ]
            
            # Blog Strategy
            blog_ideas = [
                f"Expert Review: Are {entity_name} Products Actually Worth It?",
                f"Buying Guide: Top 5 Best {entity_name} Deals & Specifications"
            ]
            
            reason = f"High Brand affinity with {eng_level} user engagement but low content volume."
            
        strategies.append({
            "entity": entity_name,
            "type": entity_type,
            "opportunity_score": score,
            "youtube": youtube_ideas,
            "pinterest": pinterest_ideas,
            "blog": blog_ideas,
            "priority_rank": idx + 1,
            "reasoning": reason
        })
        
    return strategies
