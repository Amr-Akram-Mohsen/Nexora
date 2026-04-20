from app.shared.utils.slug import generate_slug
import os, json
from typing import List
from app.domains.system.models import Brand, Category, Topic

class QueryBuilderLayer:
    def __init__(self):
        self.competitors = self._load_json("app/shared/constants/category_competitors.json")

    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def build_enhanced_query(self, title: str, category: Category, brands: List[Brand], topics: List[Topic]) -> str:
        """
        Builds an enhanced search query.
        Formula: [Brands] [Category] [Competitors] [Intent Keywords]
        """
        query_parts = []
        
        # 1. Detected Brands
        for brand in brands:
            if brand.name not in query_parts:
                query_parts.append(brand.name)
        
        # 2. Leaf Category
        if category and category.slug != generate_slug("Uncategorized"):
            query_parts.append(category.name)
            
        # 3. Competitor Expansion
        if category and category.name in self.competitors:
            # Add top 2 competitors not already in query
            count = 0
            for comp in self.competitors[category.name]:
                if comp not in query_parts:
                    query_parts.append(comp)
                    count += 1
                if count >= 2:
                    break
                    
        # 4. Intent Keywords (from Topics)
        for topic in topics:
            if topic.name not in query_parts:
                query_parts.append(topic.name)
                
        # Fallback to original title if query is too thin
        if len(query_parts) < 3:
            return title
            
        return " ".join(query_parts)
