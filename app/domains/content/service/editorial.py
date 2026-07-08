import re

def assess_video_description(description: str | None) -> dict:
    if not description:
        return {
            "has_description": False,
            "char_count": 0,
            "word_count": 0,
            "signals": [],
            "promotional_signal_count": 0,
            "confidence_score": 0.0,
            "editorial_recommendation": "display",
            "recommendation_reason": "No description provided."
        }

    char_count = len(description)
    words = description.split()
    word_count = len(words)
    lines = [line.strip() for line in description.split('\n') if line.strip()]

    signals = []
    high_count = 0
    medium_count = 0
    low_count = 0
    
    # 1. Affiliate links
    affiliate_keywords = ['bit.ly', 'amzn.to', 'goo.gl', 'promo', 'discount', 'coupon']
    if any(kw in description.lower() for kw in affiliate_keywords):
        signals.append({"label": "Contains affiliate links", "detected": True, "severity": "high"})
        high_count += 1
        
    # 2. Subscription prompts
    sub_keywords = ['subscribe', 'hit the bell', 'turn on notifications', 'join']
    if any(kw in description.lower() for kw in sub_keywords):
        signals.append({"label": "Contains subscription prompts", "detected": True, "severity": "medium"})
        medium_count += 1
        
    # 3. Social media links
    social_domains = ['.instagram.com', '.twitter.com', '.tiktok.com', 'facebook.com']
    if any(domain in description.lower() for domain in social_domains):
        signals.append({"label": "Contains social media links", "detected": True, "severity": "low"})
        low_count += 1
        
    # 4. Sponsorship disclosure
    sponsor_phrases = ['sponsored by', 'this video is brought to you', '#ad', '#sponsored']
    if any(phrase in description.lower() for phrase in sponsor_phrases):
        signals.append({"label": "Contains sponsorship disclosure", "detected": True, "severity": "high"})
        high_count += 1
        
    # 5. Timestamp list
    timestamp_pattern = re.compile(r'\d+:\d+')
    timestamp_lines = sum(1 for line in lines if timestamp_pattern.search(line))
    if timestamp_lines >= 3:
        signals.append({"label": "Contains timestamp list", "detected": True, "severity": "low"})
        low_count += 1
        
    # 6. Primarily promotional
    promo_lines = 0
    for line in lines:
        lower_line = line.lower()
        if any(kw in lower_line for kw in affiliate_keywords + sponsor_phrases) or any(domain in lower_line for domain in social_domains):
            promo_lines += 1
            
    if lines and (promo_lines / len(lines)) > 0.4:
        signals.append({"label": "Primarily promotional text", "detected": True, "severity": "high"})
        high_count += 1
        
    # 7. No editorial value
    if word_count < 20:
        signals.append({"label": "Short / no editorial value", "detected": True, "severity": "medium"})
        medium_count += 1

    score = (high_count * 0.4) + (medium_count * 0.2) + (low_count * 0.1)
    score = min(score, 1.0)
    
    if score == 0.0:
        recommendation = "display"
        reason = "No promotional signals detected."
    elif score <= 0.3:
        recommendation = "review"
        reason = "Minor signals detected. Review manually."
    elif score <= 0.6:
        recommendation = "flag"
        reason = "Significant promotional signals detected."
    else:
        recommendation = "hide"
        reason = "High confidence of promotional or non-editorial content."
        
    return {
        "has_description": True,
        "char_count": char_count,
        "word_count": word_count,
        "signals": signals,
        "promotional_signal_count": len(signals),
        "confidence_score": round(score, 2),
        "editorial_recommendation": recommendation,
        "recommendation_reason": reason
    }

def assess_article_extraction(target) -> dict:
    has_content_text = bool(getattr(target, "content_text", None))
    content_blocks = getattr(target, "content_blocks", None) or []
    has_content_blocks = bool(content_blocks)
    has_description = bool(getattr(target, "description", None))
    word_count = getattr(target, "word_count", 0)
    read_time_minutes = getattr(target, "read_time_minutes", None)
    quality_score = getattr(target, "quality_score", None)
    is_scraped = getattr(target, "is_content_scraped", False)
    extraction_status = getattr(target, "status", "unknown")
    
    # Document Structure Summary
    block_summary = {
        "total_blocks": len(content_blocks),
        "heading_count": 0,
        "paragraph_count": 0,
        "image_count": 0,
        "embed_count": 0,
        "quote_count": 0,
        "table_count": 0,
        "unknown_count": 0,
    }
    
    for block in content_blocks:
        b_type = block.get("type", "unknown") if isinstance(block, dict) else "unknown"
        if b_type == "heading": block_summary["heading_count"] += 1
        elif b_type == "paragraph": block_summary["paragraph_count"] += 1
        elif b_type == "image": block_summary["image_count"] += 1
        elif b_type == "embed": block_summary["embed_count"] += 1
        elif b_type == "blockquote": block_summary["quote_count"] += 1
        elif b_type == "table": block_summary["table_count"] += 1
        else: block_summary["unknown_count"] += 1
            
    extracted_images = getattr(target, "extracted_images", None) or []
    has_extracted_images = bool(extracted_images)
    extracted_image_count = len(extracted_images)
    
    extended_metadata = getattr(target, "extended_metadata", None) or {}
    has_extended_metadata = bool(extended_metadata)
    metadata_key_count = len(extended_metadata.keys()) if isinstance(extended_metadata, dict) else 0
    
    warnings = []
    
    if extraction_status == "failed":
        warnings.append({"label": "Enrichment pipeline failed for this article", "severity": "high"})
    if not is_scraped:
        warnings.append({"label": "Article body was not extracted (scraping skipped or failed)", "severity": "high"})
    if word_count < 100:
        warnings.append({"label": "Article body is very short — may lack editorial value", "severity": "medium"})
    if block_summary["paragraph_count"] == 0 and has_content_text:
        warnings.append({"label": "No structured paragraphs detected despite having content text", "severity": "medium"})
    if not has_description:
        warnings.append({"label": "No description/excerpt available for preview surfaces", "severity": "low"})
    if not has_extended_metadata:
        warnings.append({"label": "Publisher metadata is missing", "severity": "low"})
        
    if is_scraped and word_count >= 300 and not any(w["severity"] == "high" for w in warnings):
        extraction_health = "good"
    elif is_scraped or (not is_scraped and has_description):
        if word_count < 100 and not has_description:
            extraction_health = "thin"
        else:
            extraction_health = "partial"
    elif word_count == 0 and not has_description and not has_content_text:
        extraction_health = "empty"
    else:
        extraction_health = "thin"
        
    return {
        "has_content_text": has_content_text,
        "has_content_blocks": has_content_blocks,
        "has_description": has_description,
        "word_count": word_count,
        "read_time_minutes": read_time_minutes,
        "quality_score": quality_score,
        "is_scraped": is_scraped,
        "extraction_status": extraction_status,
        "block_summary": block_summary,
        "has_extracted_images": has_extracted_images,
        "extracted_image_count": extracted_image_count,
        "has_extended_metadata": has_extended_metadata,
        "metadata_key_count": metadata_key_count,
        "warnings": warnings,
        "extraction_health": extraction_health,
        "extended_metadata": extended_metadata
    }
