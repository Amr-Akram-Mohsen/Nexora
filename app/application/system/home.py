from app.application.content.query_service import get_contents_render_cached
from app.domains.item.service import get_filtered_items_for_home
from app.infrastructure import cache


@cache.cached(timeout=300, key_prefix="home_page_data")
def get_home_page_data():
    """
    Orchestrates data for the home page.
    """
    hero_contents = get_contents_render_cached(filter_values=("trends",), rows_count=5)
    latest_reviews = get_contents_render_cached(
        filter_values=("reviews",), rows_count=24
    )
    tech_news = get_contents_render_cached(filter_values=("news",), rows_count=24)
    tutorials = get_contents_render_cached(filter_values=("tutorials",), rows_count=24)

    # Base item data for sliders/sections
    top_deals = get_filtered_items_for_home(filter_type="deals")
    recently_added = get_filtered_items_for_home(filter_type="recent")
    interleave_pool = get_filtered_items_for_home(filter_type="random")

    def interleave(contents, items_pool):
        result = []
        pool = list(items_pool)
        for i, content in enumerate(contents):
            result.append(content)
            if (i + 1) % 3 == 0 and pool:
                result.append(pool.pop(0))
        return result

    return {
        "hero_sliders": hero_contents,
        "latest_reviews": interleave(latest_reviews, interleave_pool),
        "tech_news": interleave(tech_news, interleave_pool),
        "tutorials": interleave(tutorials, interleave_pool),
        "top_deals": top_deals,
        "recently_added": recently_added,
    }


