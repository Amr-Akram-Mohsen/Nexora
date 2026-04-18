from datetime import datetime
from typing import List
from app.domains.core.models import Brand

class ScoringLayer:
    def calculate_importance(self, source_name: str, brands: List[Brand], text: str, published_at: datetime = None) -> float:
        """
        Calculates importance_score (0.0 to 1.0).
        Factors:
        - Source weighting (NewsAPI > GNews > RSS)
        - Brand density (more explicit brands = higher score)
        - Recency boost (from today)
        """
        score = 0.2  # Base score
        
        # 1. Source Weighting
        source_norm = source_name.lower()
        if any(s in source_norm for s in ["newsapi", "verge", "wired", "techcrunch"]):
            score += 0.3
        elif any(s in source_norm for s in ["gnews", "reuters", "ap-news"]):
            score += 0.2
        elif "rss" in source_norm:
            score += 0.1
            
        # 2. Brand Density (Confidence Signal)
        if brands:
            score += min(len(brands) * 0.15, 0.4)  # Boost 0.15 per found brand, cap at 0.4
            
        # 3. Recency Weighting (Freshness Boost)
        if published_at:
            now = datetime.utcnow()
            diff = now - published_at.replace(tzinfo=None)
            if diff.days == 0:
                score += 0.1  # Small boost for same-day articles
        
        # 4. Keyword Signal (Intent/Quality)
        high_intent = ["review", "hands-on", "exclusive", "launch", "hands on", "test"]
        if any(kw in text.lower() for kw in high_intent):
            score += 0.1
            
        return min(round(score, 2), 1.0)
