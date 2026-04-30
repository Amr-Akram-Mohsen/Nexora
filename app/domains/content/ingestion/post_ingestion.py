from ..models import Post
from ..content_access import create_content, get_or_create_content
from .taxonomy import resolve_taxonomy
from ..service.command import apply_relationships

def ingest_post(session, raw_data):
    try:
        post = get_or_create_content(
            session,
            object_type="post",
            external_id=raw_data["external_id"],
            obj_factory=lambda: Post(
                title=raw_data.get("title"),
                body=raw_data.get("body"),
                external_id=raw_data["external_id"],
                platform=raw_data.get("platform", "reddit")
            )
        )

        # Resolve Taxonomy
        section, category = resolve_taxonomy(raw_data, session)

        content = create_content(
            session,
            obj=post,
            object_type="post",
            published_at=raw_data["published_at"],
            category_id=category.id,
            section_id=section.id
        )

        # Apply relationships (Topics, Brands, Facets)
        apply_relationships(content, raw_data)

        session.commit()
        return content
    except Exception:
        session.rollback()
        raise
