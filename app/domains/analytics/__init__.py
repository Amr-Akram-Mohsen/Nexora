# app/domains/interaction/service/insights/__init__.py
from app.domains.analytics.shared import get_start_date
from app.domains.analytics.content_opportunities import (
    get_top_content_data,
    get_content_opportunities,
    get_content_vs_product_performance,
    get_intent_opportunity_data,
    get_content_coverage_matrix,
    get_content_decay,
    get_content_completeness_report,
    get_user_interest_coverage_gap,
    get_category_sentiment_health
)
from app.domains.analytics.product_opportunities import (
    get_top_products_data,
    get_brand_opportunity_data,
    get_catalog_health_report,
    get_source_intelligence,
    get_content_commerce_attribution,
    get_source_authority_validation,
    get_geographic_demand_data,
    get_recommendation_commerce_chain
)
from app.domains.analytics.recommendation_performance import (
    get_recommendation_performance_data,
    get_intent_recommendation_heatmap
)
from app.domains.analytics.trends import (
    get_trending_categories_data,
    get_trending_brands_data,
    get_trending_topics_data,
    # get_entity_momentum
)
from app.domains.analytics.orchestrator import (
    get_decision_intelligence_data,
    get_executive_summary
)
from app.domains.analytics.content_strategy import generate_content_strategy
from app.domains.analytics.asset_mapping import map_content_strategy_to_assets
from app.domains.analytics.publishing_plan import generate_content_publishing_plan
from app.domains.analytics.learning_memory import load_memory_layer, save_memory_layer
from app.domains.analytics.performance_feedback import evaluate_content_performance_feedback
from app.domains.analytics.autonomous_execution import (
    execute_youtube_publish,
    execute_pinterest_publish,
    execute_pinterest_pin,
    execute_blog_publish,
    generate_execution_plan,
    process_execution_queue,
    load_execution_tasks,
    save_execution_tasks
)
from app.domains.analytics.governance import (
    generate_execution_governance_layer,
    ENABLE_LIVE_EXECUTION
)
from app.domains.analytics.distribution_intelligence import (
    get_distribution_intelligence_data
)

