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
    
    strategies = []
    
    # Limit to top 5 opportunities
    for idx, opp in enumerate(top_opps[:5]):
        entity_name = opp["entity"]
        entity_type = opp["type"].lower() # "category" or "brand"
        score = opp["score"]
        
        # 1. Content Priority Layer (priority_score: 0-100)
        opp_weight = score * 40.0 # max 40
        
        eng_val = 0.5
        if entity_type == "category":
            cat_info = cat_map.get(entity_name, {})
            demand_lvl = cat_info.get("demand", "Medium")
            if demand_lvl == "High":
                eng_val = 1.0
            elif demand_lvl == "Medium":
                eng_val = 0.6
            else:
                eng_val = 0.3
        else:
            brand_info = brand_map.get(entity_name, {})
            eng_lvl = brand_info.get("engagement_level", "Medium")
            if eng_lvl == "High":
                eng_val = 1.0
            elif eng_lvl == "Medium":
                eng_val = 0.6
            else:
                eng_val = 0.3
        eng_weight = eng_val * 30.0 # max 30
        
        gap_val = 0.5
        if entity_type == "category":
            cat_info = cat_map.get(entity_name, {})
            gap_score = cat_info.get("gap_score", "Medium Gap")
            if gap_score == "High Gap":
                gap_val = 1.0
            elif gap_score == "Medium Gap":
                gap_val = 0.6
            else:
                gap_val = 0.3
        else:
            brand_info = brand_map.get(entity_name, {})
            has_opp = brand_info.get("opportunity", False)
            if has_opp:
                gap_val = 1.0
            else:
                gap_val = 0.4
        gap_weight = gap_val * 30.0 # max 30
        
        priority_score = round(opp_weight + eng_weight + gap_weight, 1)
        
        # 2. Content Lifecycle Tag (evergreen / trending / seasonal)
        lifecycle_tag = "evergreen"
        if score >= 0.8:
            lifecycle_tag = "trending"
        elif any(x in entity_name.lower() for x in ["gift", "holiday", "winter", "summer", "ramadan", "eid"]):
            lifecycle_tag = "seasonal"
        else:
            intent_info = intent_map.get(entity_name, {}) if entity_type == "category" else None
            if intent_info:
                opt_str = intent_info.get("opportunity", "").lower()
                if any(x in opt_str for x in ["news", "trend"]):
                    lifecycle_tag = "trending"
                elif "gift" in opt_str:
                    lifecycle_tag = "seasonal"
        
        # 3. Platform Weighting
        intent_info = intent_map.get(entity_name, {}) if entity_type == "category" else None
        intent_opt = intent_info.get("opportunity", "buying-guide") if intent_info else "buying-guide"
        
        is_comparison_review = "comparison" in intent_opt.lower() or "review" in intent_opt.lower() or entity_type == "brand"
        is_visual = "tutorial" in intent_opt.lower() or "guide" in intent_opt.lower() or "gift" in intent_opt.lower()
        is_evergreen = lifecycle_tag == "evergreen"
        
        if is_comparison_review:
            youtube_count = 3
            pinterest_count = 1
            blog_count = 1
        elif is_visual:
            youtube_count = 2
            pinterest_count = 2
            blog_count = 1
        elif is_evergreen:
            youtube_count = 2
            pinterest_count = 1
            blog_count = 2
        else:
            youtube_count = 2
            pinterest_count = 1
            blog_count = 1

        # 4 & 5. Deduplicated & Enhanced templates by template_set_idx = idx % 5
        template_set_idx = idx % 5
        
        if entity_type == "category":
            yt_templates = [
                [
                    f"I Tested Every {entity_name} So You Don't Have To! (Honest Review)",
                    f"Which {entity_name} is the Absolute Best? Head-to-Head Comparison",
                    f"Ultimate {entity_name} Comparison: Don't Waste Your Money!"
                ],
                [
                    f"Top 5 Best {entity_name} of 2026: The Definitive Review",
                    f"Cheapest vs Most Expensive {entity_name} (Tested!)",
                    f"{entity_name} Face-Off: Which Brand Actually Wins?"
                ],
                [
                    f"How to Choose the Perfect {entity_name}: Complete Buying Guide",
                    f"5 Critical {entity_name} Mistakes 90% of Beginners Make!",
                    f"Watch This Before Buying A {entity_name}!"
                ],
                [
                    f"The Only {entity_name} Video Guide You Need to Watch!",
                    f"Everything You Need to Know About {entity_name} (Walkthrough)",
                    f"Expert Tips: Setup & Configure Your {entity_name} Perfectly"
                ],
                [
                    f"10 {entity_name} Secrets Manufacturers Don't Want You to Know!",
                    f"Is this the Future of {entity_name}? (In-Depth Review)",
                    f"Tested: What is the Best {entity_name} for the Price?"
                ]
            ]
            
            pin_templates = [
                [
                    f"📸 INFOGRAPHIC: The Ultimate {entity_name} Selection Flowchart",
                    f"🗺️ VISUAL ROADMAP: How to Choose Your Next {entity_name}"
                ],
                [
                    f"🗺️ VISUAL ROADMAP: How to Set Up Your New {entity_name}",
                    f"💡 QUICK CHECKLIST: Top 5 Features in {entity_name}"
                ],
                [
                    f"📊 COMPARISON TABLE: {entity_name} Specifications Breakdown",
                    f"⭐ VISUAL SPECS: Evolution of Top-Rated {entity_name} Models"
                ],
                [
                    f"💡 QUICK CHECKLIST: 10 Features to Look for in {entity_name}",
                    f"📸 INFOGRAPHIC: Complete Guide to {entity_name}"
                ],
                [
                    f"⭐ VISUAL SPECS: Evolution of Top-Rated {entity_name} Models",
                    f"🗺️ VISUAL ROADMAP: Setup Checklist for {entity_name}"
                ]
            ]
            
            blog_templates = [
                [
                    f"Best {entity_name} in Saudi Arabia: 2026 Buying Guide & Reviews",
                    f"SEO Analysis: Top {entity_name} Trends & Search Insights"
                ],
                [
                    f"Unbiased {entity_name} Comparison: Pros, Cons & Specifications",
                    f"Direct Comparison: Head-to-Head {entity_name} Brand Matchup"
                ],
                [
                    f"In-Depth {entity_name} Review: Is It Worth the Price? [Saudi Arabia]",
                    f"Detailed Breakdown: Pros and Cons of Modern {entity_name}"
                ],
                [
                    f"Step-by-Step Guide: How to Select and Use {entity_name} Effectively",
                    f"Ultimate Setup Tutorial: Getting Started with {entity_name}"
                ],
                [
                    f"Top 5 Rated {entity_name} Models: Specifications & Price Breakdown",
                    f"Affordable {entity_name}: Best Value Models Reviewed"
                ]
            ]
            
            cat_info = cat_map.get(entity_name, {})
            gap_status = cat_info.get("gap_score", "Medium Gap")
            demand_lvl = cat_info.get("demand", "Medium")
            reason = f"High priority Category with {demand_lvl} demand and {gap_status.lower()}."
            
        else: # Brand opportunity
            yt_templates = [
                [
                    f"The Truth About {entity_name} Products (Honest Video Review)",
                    f"{entity_name} vs The Competition: Is It Worth the Premium?",
                    f"I Bought the Newest {entity_name} Products... Here's My Verdict!"
                ],
                [
                    f"Testing {entity_name} Durability: Watch Before Buying!",
                    f"Top 5 {entity_name} Features You Probably Didn't Know About",
                    f"Direct Brand Battle: {entity_name} vs Competitors"
                ],
                [
                    f"How to Set Up & Optimize Your {entity_name} Devices",
                    f"Complete {entity_name} Setup Tutorial for Beginners",
                    f"Step-by-Step {entity_name} Setup walkthrough"
                ],
                [
                    f"Unboxing the Newest Releases from {entity_name}!",
                    f"Watch This {entity_name} Video Walkthrough First!",
                    f"Is {entity_name} Worth It? Unboxing & Verdict"
                ],
                [
                    f"Is {entity_name} Still the Best Brand? (Testing & Analysis)",
                    f"The Ultimate {entity_name} Brand Guide & Specs Overview",
                    f"My Honest {entity_name} Brand Review"
                ]
            ]
            
            pin_templates = [
                [
                    f"📊 COMPARISON CHART: {entity_name} vs Competitor Brands",
                    f"📸 VISUAL SPECIFICATION: Best {entity_name} Model Features"
                ],
                [
                    f"📸 VISUAL SPECIFICATION: Best {entity_name} Model Features",
                    f"💡 DESIGN ROADMAP: Setup & Interface of {entity_name}"
                ],
                [
                    f"💡 DESIGN ROADMAP: Setup & Interface of {entity_name}",
                    f"🗺️ STEP-BY-STEP PIN: Unboxing & Features Checklist for {entity_name}"
                ],
                [
                    f"🗺️ STEP-BY-STEP PIN: Unboxing & Features Checklist for {entity_name}",
                    f"⭐ BRAND INFOGRAPHIC: {entity_name} Buying Cheat Sheet"
                ],
                [
                    f"⭐ BRAND INFOGRAPHIC: {entity_name} Buying Cheat Sheet",
                    f"📊 COMPARISON CHART: {entity_name} Models Ranked"
                ]
            ]
            
            blog_templates = [
                [
                    f"Expert Review: Is {entity_name} Worth the Hype? [Saudi Arabia]",
                    f"{entity_name} Brand Guide: Specifications, Features & Models"
                ],
                [
                    f"{entity_name} Brand Guide: Specifications, Features & Models",
                    f"Buying Guide: Top 5 Best {entity_name} Deals & Reviews"
                ],
                [
                    f"Buying Guide: Top 5 Best {entity_name} Deals & Reviews",
                    f"Direct Comparison: {entity_name} vs Other Top Brands"
                ],
                [
                    f"Direct Comparison: {entity_name} vs Other Top Brands",
                    f"Unbiased Review: {entity_name} Pros & Cons Analysis"
                ],
                [
                    f"Unbiased Review: {entity_name} Pros & Cons Analysis",
                    f"Complete Breakdown: Everything you need to know about {entity_name}"
                ]
            ]
            
            brand_info = brand_map.get(entity_name, {})
            eng_level = brand_info.get("engagement_level", "Medium")
            reason = f"High Brand affinity with {eng_level} user engagement but low content volume."

        youtube_ideas = yt_templates[template_set_idx][:youtube_count]
        pinterest_ideas = pin_templates[template_set_idx][:pinterest_count]
        blog_ideas = blog_templates[template_set_idx][:blog_count]
        
        # Format reasoning with priority score and lifecycle tag for DOM representation
        reason_enhanced = f"{reason} | Priority Score: {priority_score} | Lifecycle: {lifecycle_tag}"

        strategies.append({
            "entity": entity_name,
            "type": entity_type,
            "opportunity_score": score,
            "priority_score": priority_score,
            "lifecycle_tag": lifecycle_tag,
            "youtube": youtube_ideas,
            "pinterest": pinterest_ideas,
            "blog": blog_ideas,
            "priority_rank": idx + 1,
            "reasoning": reason_enhanced
        })
        
    return strategies
