# app/integrations/discovery.py

import logging

from typing import Dict, List

from app.shared.constants.taxonomy import TAXONOMY
from app.shared.utils.slug import generate_slug
from app.shared.utils.logging import log_integration_warning

from app.shared.constants.query_intelligence import (
    DEFAULT_SOURCE_ALIGNMENT,
    CATEGORY_SOURCE_OVERRIDES,
    SECTION_DEFAULT_INTENTS,
    CATEGORY_TOPIC_MAP,
)
from app.shared.constants.source_profiles import SOURCE_PROFILES

from .query_generator import (
    generate_discovery_queries,
)

logger = logging.getLogger(__name__)


class DiscoveryManager:
    def __init__(self):
        self.taxonomy = TAXONOMY

    def get_queries_by_section(
        self, source_filter: str | None = None
    ) -> Dict[str, Dict[str, List[Dict]]]:

        registry = {}

        sections = self.taxonomy.get("sections", [])
        categories_data = self.taxonomy.get("categories", [])

        logger.debug(
            "[DISCOVERY] source=%s  sections=%d  categories=%d",
            source_filter or "(all)",
            len(sections),
            len(categories_data),
        )

        if not sections:
            log_integration_warning(
                logger,
                "discovery",
                reason="no_sections_in_taxonomy",
            )

        if not categories_data:
            log_integration_warning(
                logger,
                "discovery",
                reason="no_categories_in_taxonomy",
            )

        for sec in sections:
            sec_slug = generate_slug(sec["name"])
            registry[sec_slug] = {}

            category_index = 0  # stable counter for deterministic modifier slots

            for cat_group in categories_data:
                parent_slug = generate_slug(cat_group["name"])

                for child in cat_group.get("children", []):
                    cat_slug = generate_slug(child["name"])

                    if cat_slug == "uncategorized":
                        continue

                    # Temporarily skip categories the user already has enough data for
                    if cat_slug in ["smartphones", "laptops"]:
                        continue

                    # --------------------------------------------------
                    # Source alignment (primary gate)
                    # --------------------------------------------------

                    override_sources = CATEGORY_SOURCE_OVERRIDES.get(
                        parent_slug, {}
                    ).get(sec_slug)
                    has_override = override_sources is not None
                    allowed_sources = (
                        override_sources
                        if has_override
                        else DEFAULT_SOURCE_ALIGNMENT.get(sec_slug, [])
                    )

                    if source_filter and source_filter not in allowed_sources:
                        logger.debug(
                            "[DISCOVERY] rejected  source=%s  section=%s  category=%s",
                            source_filter,
                            sec_slug,
                            cat_slug,
                        )
                        continue

                    # --------------------------------------------------
                    # SourceProfile.allowed_sections (secondary gate)
                    # Only enforced when no category-level override is present.
                    # If an explicit override includes this source for this
                    # section, we trust that intentional decision over the
                    # profile-level hint (e.g. YouTube used for perfumes:news).
                    # --------------------------------------------------

                    if source_filter and not has_override:
                        profile = SOURCE_PROFILES.get(source_filter)
                        if (
                            profile
                            and profile.allowed_sections
                            and sec_slug not in profile.allowed_sections
                        ):
                            logger.debug(
                                "[DISCOVERY] profile_rejected  source=%s  section=%s  category=%s",
                                source_filter,
                                sec_slug,
                                cat_slug,
                            )
                            continue

                    # --------------------------------------------------
                    # Query generation
                    # --------------------------------------------------

                    queries = generate_discovery_queries(
                        source=source_filter or "generic",
                        section_slug=sec_slug,
                        category_name=child["name"],
                        category_slug=cat_slug,
                        category_group_name=cat_group["name"],
                        keywords=child.get("search_keywords", []),
                        intents=SECTION_DEFAULT_INTENTS.get(
                            sec_slug,
                            ["Review"],
                        ),
                        topics=CATEGORY_TOPIC_MAP.get(cat_slug, []),
                        facets_data=self.taxonomy.get("facets", {}),
                        category_query_index=category_index,
                    )

                    category_index += 1

                    if not queries:
                        continue

                    full_cat_slug = f"{parent_slug}:{cat_slug}"

                    registry[sec_slug][full_cat_slug] = queries

        total_queries = sum(
            len(qs) for sec_cats in registry.values() for qs in sec_cats.values()
        )
        # Count only sections that actually produced queries (after source filtering).
        # This is what operators care about — not the total taxonomy sections.
        sections_with_queries = sum(1 for sec_cats in registry.values() if sec_cats)

        logger.info(
            "[DISCOVERY] source=%s  queries=%d  sections_with_queries=%d/%d",
            source_filter or "(all)",
            total_queries,
            sections_with_queries,
            len(registry),
        )

        return registry

    def get_section_slugs(self) -> List[str]:
        return [generate_slug(s["name"]) for s in self.taxonomy.get("sections", [])]
