import re

def score_content_quality(html: str, text: str) -> float:
    """
    Scores the quality of the content between 0.0 and 1.0.
    Based on structure, paragraph density, noise penalties, and length.
    """
    if not text or not text.strip():
        return 0.0

    word_count = len(text.split())
    if word_count < 50:
        return 0.1  # Too short to be useful

    score = 0.0

    # 1. Word count (up to 0.2 points)
    if word_count > 400:
        score += 0.2
    elif word_count > 200:
        score += 0.15
    elif word_count > 100:
        score += 0.1

    # 2. Structural Rewards (up to 0.4 points)
    if html:
        headings = len(re.findall(r'<h[1-6][^>]*>', html, re.IGNORECASE))
        lists = len(re.findall(r'<ul[^>]*>|<ol[^>]*>|<li[^>]*>', html, re.IGNORECASE))
        images = len(re.findall(r'<img[^>]*>', html, re.IGNORECASE))
        paragraphs = len(re.findall(r'<p[^>]*>', html, re.IGNORECASE))
        
        if headings > 0:
            score += min(0.15, headings * 0.05)
        if lists > 0:
            score += min(0.1, lists * 0.02)
        if images > 0:
            score += min(0.05, images * 0.05)
            
        # Meaningful paragraph segmentation (reward good density)
        if paragraphs > 0:
            words_per_p = word_count / paragraphs
            if 20 <= words_per_p <= 80:
                score += 0.1
    else:
        paragraphs = len(text.split('\n\n'))

    # 3. Text Cadence & Density (up to 0.4 points)
    sentences = len(re.split(r'[.!?]+', text))
    if sentences > 0:
        words_per_sentence = word_count / sentences
        if 10 <= words_per_sentence <= 25:
            score += 0.4
        elif 5 <= words_per_sentence < 10 or 25 < words_per_sentence <= 40:
            score += 0.2
        else:
            score += 0.05

    # 4. Penalties (subtracts points)
    # Repeated phrases (basic check)
    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 20]
    if len(lines) > 5:
        unique_lines = set(lines)
        repetition_ratio = 1.0 - (len(unique_lines) / len(lines))
        if repetition_ratio > 0.3:
            score -= 0.3
        elif repetition_ratio > 0.1:
            score -= 0.1

    # Low paragraph density penalty
    if sentences > 10 and paragraphs < 2:
        score -= 0.2

    return round(min(1.0, max(0.0, score)), 3)
