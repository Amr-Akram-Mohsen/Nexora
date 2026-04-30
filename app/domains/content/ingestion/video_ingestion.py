from ..models import Video
from ..content_access import create_content, get_or_create_content
from .taxonomy import resolve_taxonomy
from ..service.command import apply_relationships

def ingest_video(session, raw_data):
    try:
        video = get_or_create_content(
            session,
            object_type="video",
            external_id=raw_data["external_id"],
            obj_factory=lambda: Video(
                title=raw_data["title"],
                description=raw_data["description"],
                external_id=raw_data["external_id"],
                platform=raw_data.get("platform", "youtube")
            )
        )

        # Resolve Taxonomy
        section, category = resolve_taxonomy(raw_data, session)

        content = create_content(
            session,
            obj=video,
            object_type="video",
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
