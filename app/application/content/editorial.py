def assess_publishing_readiness(content_dto: dict, extraction_assessment: dict | None = None) -> dict:
    """
    Assesses whether a content product is ready to be published based on its serialized DTO
    and an optional extraction assessment (for articles).
    """
    checklist = []
    score = 0
    total_weight = 0
    blocking_issues = []
    
    def add_check(label, passed, weight, is_blocking=False):
        nonlocal score, total_weight
        checklist.append({"label": label, "passed": passed, "weight": weight})
        total_weight += weight
        if passed:
            score += weight
        elif is_blocking or weight >= 15:
            blocking_issues.append(label)
            
    # Base checks (apply to all content types)
    add_check("Title present", bool(content_dto.get("title")), 15, is_blocking=True)
    
    category = content_dto.get("category")
    has_valid_category = bool(category and category.get("slug") and category.get("slug") != "uncategorized")
    add_check("Category assigned (not Uncategorized)", has_valid_category, 15, is_blocking=True)
    
    add_check("Section assigned", bool(content_dto.get("section")), 10)
    add_check("Topics tagged", bool(content_dto.get("topics")), 10)
    add_check("Brands tagged", bool(content_dto.get("brands")), 10)
    add_check("Source linked", bool(content_dto.get("source") or content_dto.get("sources")), 10)
    
    # We don't have "duplicate title" in the DTO directly unless we pass it, we can skip or assume true.
    # Let's assume it's true for now, as that's normally checked at list view.
    
    # Type-specific checks
    object_type = content_dto.get("object_type")
    
    if object_type == "article" and extraction_assessment:
        has_extracted_body = extraction_assessment.get("has_content_html") or extraction_assessment.get("has_content_text")
        add_check("Body content extracted", has_extracted_body, 20, is_blocking=True)
        
        word_count = extraction_assessment.get("word_count", 0)
        add_check("Sufficient word count (≥ 100 words)", word_count >= 100, 10)
        
        status = extraction_assessment.get("extraction_status")
        add_check("No pipeline failures", status != "failed", 15, is_blocking=True)
        
    elif object_type == "video":
        add_check("Platform assigned", bool(content_dto.get("platform")), 15)
        add_check("Video URL or ID present", bool(content_dto.get("external_id") or content_dto.get("original_url")), 15, is_blocking=True)
        
    # Calculate final score out of 100
    normalized_score = int((score / total_weight) * 100) if total_weight > 0 else 0
    
    if len(blocking_issues) > 0:
        readiness_level = "not_ready"
    elif normalized_score == 100:
        readiness_level = "ready"
    elif normalized_score >= 80:
        readiness_level = "almost_ready"
    else:
        readiness_level = "needs_work"
        
    return {
        "readiness_score": normalized_score,
        "readiness_level": readiness_level,
        "checklist": checklist,
        "blocking_issues": blocking_issues
    }
