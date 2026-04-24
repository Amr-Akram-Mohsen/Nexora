# app/integrations/enrichment/query_builder.py
class QueryBuilderLayer:
    def build_enhanced_query(self, title, category, brands, topics) -> str:
        """
        Builds an enhanced search query.
        Formula: [Brands] [Category] [Competitors] [Intent Keywords]
        """
        query_parts = []
        
        # 1. Brands (HIGH PRECISION)
        for brand in brands:
            query_parts.append(brand.name)
        
        # 2. Category (STRICT)
        if category:
            query_parts.append(category.name)
            
        # 4. Intent (from topics or facets later)
        for topic in topics:
            query_parts.append(topic.name)

        return " ".join(query_parts) if query_parts else title
