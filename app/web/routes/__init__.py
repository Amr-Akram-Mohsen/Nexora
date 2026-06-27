from .admin import (
    api_user_bp,
    api_content_bp,
    api_item_bp,
    api_interaction_bp,
    api_dashboard_bp,
    api_ingestion_bp,
    api_system_bp,
    api_taxonomy_bp,
    api_recommendation_bp,
    api_provider_bp,
    api_insights_bp,
    api_distribution_bp,
    api_subscribers_bp,
    api_audience_analytics_bp,
    api_admin_bp
)

from .user import bp as user_bp
from .content import bp as content_bp
from .item import bp as item_bp
from .interaction import bp as interaction_bp
from .recommendation import bp as recommendation_bp
from .system import bp as system_bp

