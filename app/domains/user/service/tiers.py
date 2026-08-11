TIER_THRESHOLDS = [(200, 'Power User', 'power_user'), (50, 'High', 'high'), (10, 'Medium', 'medium'), (0, 'Low', 'low')]
def score_to_tier(score: float, snake_case: bool=False) -> str:
    for threshold, label, snake_label in TIER_THRESHOLDS:
        if score >= threshold:
            return snake_label if snake_case else label
    return 'low' if snake_case else 'Low'