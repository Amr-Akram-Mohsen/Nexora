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
    ``"electronics:smartphones"``.  The DB stores leaf categories under their
    leaf slug (``"smartphones"``).  This helper extracts the leaf part so the
    DB lookup always succeeds.

    Examples::

        "electronics:smartphones" → "smartphones"
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
      3. Parent slug (e.g. "electronics") – broad fallback
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

    # 1. Preferred: leaf slug  (strips "electronics:" prefix)
    leaf = _leaf_slug(raw_cat_slug)
    category = Category.get_by_slug(leaf, session) if leaf else None

    # 2. Composite slug verbatim  (unlikely to be in DB but safe to try)
    if not category and raw_cat_slug and raw_cat_slug != leaf:
        category = Category.get_by_slug(raw_cat_slug, session)

    # 3. Parent slug  (broad category fallback, e.g. "electronics")
    if not category:
        parent = _parent_slug(raw_cat_slug)
        if parent:
            category = Category.get_by_slug(parent, session)
            if category:
                logger.debug(
                    "[TAXONOMY] category_fallback  raw=%s  resolved_as=parent(%s)",
                    raw_cat_slug,
                    parent,
                )

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
