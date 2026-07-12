import logging
from app.core.extensions import db
from app.domains.taxonomy.models import Section, Category

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Slug normalisation helpers
# ---------------------------------------------------------------------------

def _leaf_slug(slug: str) -> str:
    """
    Strip the parent prefix from a composite slug.

    The discovery layer produces composite category keys like
    ``"technology:smartphones"``.  The DB stores leaf categories under their
    leaf slug (``"smartphones"``).  This helper extracts the leaf part so the
    DB lookup always succeeds.

    Examples::

        "technology:smartphones" → "smartphones"
        "perfumes:niche-artisanal" → "niche-artisanal"
        "smartphones"              → "smartphones"   (already a leaf)
    """
    if slug and ":" in slug:
        return slug.split(":")[-1]
    return slug or ""


def _parent_slug(slug: str) -> str:
    """Return the parent part of a composite slug, or empty string."""
    if slug and ":" in slug:
        return slug.split(":")[0]
    return ""


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------

def resolve_taxonomy(data, session=None):
    """
    Resolve section_slug and category_slug from *data* into DB objects.

    Resolution order for the category:
      1. Leaf slug (e.g. "smartphones")
      2. Composite slug as-is (legacy / edge-case)
      3. Parent slug (e.g. "technology") – broad fallback
      4. "uncategorized" – last resort

    Falls back to "news" for the section when the slug is missing/unknown.
    """
    if session is None:
        session = db.session

    # ── Section ──────────────────────────────────────────────────────────
    section_slug = data.get("section_slug") or "news"
    section = Section.get_by_slug(section_slug, session)
    if not section:
        section = Section.get_by_slug("news", session)

    # ── Category ─────────────────────────────────────────────────────────
    raw_cat_slug = data.get("category_slug") or ""

    # 1. Preferred: leaf slug  (strips "technology:" prefix)
    leaf = _leaf_slug(raw_cat_slug)
    category = Category.get_by_slug(leaf, session) if leaf else None

    # 2. Composite slug verbatim  (unlikely to be in DB but safe to try)
    if not category and raw_cat_slug and raw_cat_slug != leaf:
        category = Category.get_by_slug(raw_cat_slug, session)

    # 3. Create missing category dynamically
    if not category and leaf and leaf != "uncategorized":
        logger.info(
            "[TAXONOMY] creating_missing_category  raw=%s  leaf=%s",
            raw_cat_slug,
            leaf,
        )
        name = leaf.replace("-", " ").title()
        
        # Try to resolve parent to link it properly
        parent_slug = _parent_slug(raw_cat_slug)
        parent_cat = Category.get_by_slug(parent_slug, session) if parent_slug and parent_slug != leaf else None
        
        category = Category.get_or_create(name=name, session=session, parent=parent_cat, is_leaf=True)

    # 4. Uncategorized  (absolute last resort)
    if not category:
        logger.warning(
            "[TAXONOMY] uncategorized_fallback  raw=%s  leaf=%s  "
            "Check that this slug exists in the DB.",
            raw_cat_slug,
            leaf,
        )
        category = Category.get_by_slug("uncategorized", session)

    return section, category
