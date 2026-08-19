"""
Consolidated content ingestion engine.

Contains taxonomy resolution, polymorphic model creation, diffbot enrichment,
and type-specific ingestors for articles, videos, and posts.
"""
from __future__ import annotations

import datetime
import logging
from sqlalchemy.exc import IntegrityError

from app.core.extensions import db
from app.domains.content.models import Article, Video, Post
from app.domains.content.models.author import Author
from app.domains.content.models.video import VideoComment
from app.domains.content.models.content import Content
from app.domains.content.service.command import apply_relationships, create_content, get_or_create_content
from app.domains.content.service import populate_content_search_fields
from app.domains.content.service.normalization import (
    parse_date,
    normalize_article_data,
    normalize_video_data,
    normalize_post_data,
)
from app.domains.taxonomy.models import Section, Category
from app.shared.dto.ingestion import EnrichedItemDTO
from app.shared.utils.logging import log_item_skipped

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Taxonomy Resolution
# ---------------------------------------------------------------------------


def _leaf_slug(slug: str) -> str:
    """Extract leaf portion from composite slug (e.g. 'technology:smartphones' -> 'smartphones')."""
    if slug and ":" in slug:
        return slug.split(":")[-1]
    return slug or ""


def _parent_slug(slug: str) -> str:
    """Return the parent part of a composite slug, or empty string."""
    if slug and ":" in slug:
        return slug.split(":")[0]
    return ""


def resolve_taxonomy(data: dict, session=None):
    """
    Resolve section_slug and category_slug from *data* into DB objects.
    Falls back gracefully to 'news' section and creates missing leaf categories if needed.
    """
    if session is None:
        session = db.session

    section_slug = data.get("section_slug") or "news"
    section = Section.get_by_slug(section_slug, session)
    if not section:
        section = Section.get_by_slug("news", session)

    raw_cat_slug = data.get("category_slug") or ""
    leaf = _leaf_slug(raw_cat_slug)
    category = Category.get_by_slug(leaf, session) if leaf else None

    if not category and raw_cat_slug and raw_cat_slug != leaf:
        category = Category.get_by_slug(raw_cat_slug, session)

    if not category and leaf and leaf != "uncategorized":
        logger.info("[TAXONOMY] creating_missing_category  raw=%s  leaf=%s", raw_cat_slug, leaf)
        name = leaf.replace("-", " ").title()
        parent_slug = _parent_slug(raw_cat_slug)
        parent_cat = Category.get_by_slug(parent_slug, session) if parent_slug and parent_slug != leaf else None
        category = Category.get_or_create(name=name, session=session, parent=parent_cat, is_leaf=True)

    if not category:
        category = Category.get_by_slug("uncategorized", session)

    return section, category


# ---------------------------------------------------------------------------
# Generic Ingestion Engine
# ---------------------------------------------------------------------------


def generic_ingest(session, object_type: str, raw_data: dict, factory_func, update_func=None):
    """Standardized ingestion flow for any polymorphic content type."""
    try:
        with session.begin_nested():
            obj, is_new = get_or_create_content(
                object_type=object_type,
                external_id=raw_data.get("external_id"),
                obj_factory=lambda: factory_func(raw_data),
                title_fallback=raw_data.get("title"),
                url_fallback=raw_data.get("url"),
                session=session,
                canonical_url=raw_data.get("canonical_url"),
            )

            if not obj:
                return None, "skipped"

            was_obj_updated = False
            if not is_new and update_func:
                was_obj_updated = update_func(obj, raw_data)
                if was_obj_updated:
                    session.add(obj)
                    session.flush()

            section, category = resolve_taxonomy(raw_data, session)

            content, was_content_updated = create_content(
                obj=obj,
                object_type=object_type,
                published_at=raw_data.get("published_at"),
                session=session,
                category_id=category.id if category else None,
                section_id=section.id if section else None,
                is_published=raw_data.get("is_published", False),
            )

            updated_relationships = {}
            if content:
                updated_relationships = apply_relationships(content, raw_data, session=session)

            populate_content_search_fields(content, obj, object_type)

            if is_new:
                return content, "created"

            if updated_relationships or was_content_updated or was_obj_updated:
                return content, updated_relationships or "updated"

            return None, "skipped"

    except IntegrityError:
        source = raw_data.get("source", "unknown")
        if isinstance(source, dict):
            source = source.get("name", "unknown")

        log_item_skipped(
            logger,
            source=source,
            title=raw_data.get("title", "untitled"),
            reason="duplicate_integrity_error",
            external_id=raw_data.get("external_id"),
        )
        return None, "skipped"
    except Exception as e:
        source = raw_data.get("source", "unknown")
        if isinstance(source, dict):
            source = source.get("name", "unknown")

        logger.error(
            "[INGEST] critical_failure  type=%s  title=\"%s\"  source=%s  err=%s",
            object_type,
            raw_data.get("title", "unknown")[:60],
            source,
            e,
            stacklevel=2,
        )
        raise


# ---------------------------------------------------------------------------
# Article Ingestion & Diffbot Enrichment
# ---------------------------------------------------------------------------


def calculate_enrichment_priority(data: dict) -> float:
    """Calculates priority for Diffbot enrichment using pre-enrichment signals."""
    priority = 0.0
    quality_score = data.get("quality_score") or 0.0
    priority += quality_score * 2.0

    er_source = data.get("er_source")
    if isinstance(er_source, dict):
        importance = er_source.get("importance", 0.0)
        try:
            priority += float(importance)
        except (ValueError, TypeError):
            pass

    er_concepts = data.get("er_concepts")
    if isinstance(er_concepts, list):
        priority += min(1.0, len(er_concepts) * 0.1)

    er_categories = data.get("er_categories")
    if isinstance(er_categories, list):
        priority += min(1.0, len(er_categories) * 0.2)

    er_location = data.get("er_location")
    if isinstance(er_location, dict) and er_location:
        priority += 0.2

    if data.get("er_event_uri") or data.get("er_event_data"):
        priority += 1.5

    published_at = data.get("published_at")
    if published_at:
        pub_date = parse_date(published_at)
        if pub_date:
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            age_hours = (now - pub_date).total_seconds() / 3600.0
            if age_hours >= 0:
                freshness_boost = max(0.0, 1.0 - (age_hours / 48.0))
                priority += freshness_boost

    return float(priority)


def _sync_authors(authors_data, existing_authors=None, session=None):
    if session is None:
        session = db.session
    if existing_authors is None:
        existing_authors = []

    result_authors = list(existing_authors)
    for author_data in authors_data:
        if isinstance(author_data, str):
            author_data = {"name": author_data}

        name = author_data.get("name")
        if not name or name.strip().lower() in ("see full bio", "full bio", "author", "by"):
            continue

        uri = author_data.get("uri")
        url = author_data.get("link") or author_data.get("authorUrl") or author_data.get("url")
        type_val = author_data.get("type", "author")
        is_agency = author_data.get("isAgency", False)

        author_obj = Author.get_or_create(
            session=session,
            name=name,
            uri=uri,
            url=url,
            type_val=type_val,
            is_agency=is_agency,
        )
        if author_obj and author_obj not in result_authors:
            result_authors.append(author_obj)

    return result_authors


def create_article_model(data: dict) -> Article:
    authors_data = data.get("authors") or ([data.get("author")] if data.get("author") else [])
    author_objs = _sync_authors(authors_data)

    return Article(
        title=data.get("title"),
        description=data.get("description"),
        body=data.get("body"),
        content_text=data.get("content_text"),
        content_html=data.get("content_html"),
        word_count=data.get("word_count"),
        quality_score=data.get("quality_score", 0.0),
        ingestion_method=data.get("ingestion_method"),
        status=data.get("status", "discovered"),
        image_url=data.get("image_url"),
        authors=author_objs,
        language=data.get("language"),
        sentiment_score=data.get("sentiment_score"),
        extended_metadata=data.get("extended_metadata"),
        images=data.get("images"),
        videos=data.get("videos"),
        summary=data.get("summary"),
        enrichment_priority=calculate_enrichment_priority(data),
    )


def update_article_model(obj: Article, data: dict) -> bool:
    changed = False
    if data.get("body") and not obj.body:
        obj.body = data.get("body")
        changed = True
    if data.get("word_count") and not obj.word_count:
        obj.word_count = data.get("word_count")
        changed = True
    if data.get("authors"):
        new_authors = _sync_authors(data.get("authors"), existing_authors=obj.authors)
        if len(new_authors) > len(obj.authors or []):
            obj.authors = new_authors
            changed = True
    if data.get("language") and not obj.language:
        obj.language = data.get("language")
        changed = True
    if data.get("sentiment_score") is not None and obj.sentiment_score is None:
        obj.sentiment_score = data.get("sentiment_score")
        changed = True
    return changed


def process_diffbot_enrichment(article: Article, diffbot_data: dict, session) -> bool:
    """Applies Diffbot enrichment payload to a discovered Article."""
    if not diffbot_data or "metadata" not in diffbot_data:
        article.status = "failed"
        return False

    obj = diffbot_data["metadata"]
    article.content_text = obj.get("text")
    article.content_html = obj.get("html")

    if not article.language:
        article.language = obj.get("humanLanguage")
    if not article.word_count:
        article.word_count = len(article.content_text.split()) if article.content_text else 0

    if article.sentiment_score is None:
        article.sentiment_score = obj.get("sentiment")

    summary = obj.get("summary")
    if summary:
        import re
        from difflib import SequenceMatcher

        def _norm(t):
            return re.sub(r"[^a-z0-9]", "", (t or "").lower())

        norm_sum = _norm(summary)
        if len(norm_sum) > 20:
            norm_desc = _norm(article.description)
            norm_text_start = _norm(article.content_text[: len(summary) * 2 + 400]) if article.content_text else ""
            is_redundant = False
            if norm_sum in norm_text_start or (norm_desc and (norm_sum in norm_desc or norm_desc in norm_sum)):
                is_redundant = True
            elif norm_desc and SequenceMatcher(None, norm_sum, norm_desc).ratio() > 0.85:
                is_redundant = True
            elif norm_text_start:
                prefix = norm_text_start[: len(norm_sum) + 100]
                if len(prefix) > 20:
                    match = SequenceMatcher(None, norm_sum, prefix).find_longest_match(0, len(norm_sum), 0, len(prefix))
                    if match.size > len(norm_sum) * 0.8:
                        is_redundant = True
                    elif SequenceMatcher(None, norm_sum, norm_text_start[: len(norm_sum)]).ratio() > 0.85:
                        is_redundant = True

            if is_redundant:
                summary = None

    article.summary = summary
    if "images" in obj:
        article.images = obj.get("images", [])
    if "videos" in obj:
        article.videos = obj.get("videos", [])

    diffbot_authors_data = []
    if obj.get("authors"):
        diffbot_authors_data = obj.get("authors")
    elif obj.get("author"):
        author_val = obj.get("author")
        diffbot_authors_data = [{"name": author_val}] if isinstance(author_val, str) else [author_val]

    if diffbot_authors_data:
        article.authors = _sync_authors(diffbot_authors_data, existing_authors=article.authors, session=session)

    if "tags" in obj:
        from app.domains.relationships import ContentEntity
        from app.domains.taxonomy.models import Entity

        content = session.query(Content).filter_by(object_type="article", object_id=article.id).first()
        if content:
            for tag in obj.get("tags", []):
                label = tag.get("label")
                uri = tag.get("uri")
                score = tag.get("score", 0.0)
                if not label:
                    continue

                entity = Entity.get_or_create(
                    name=label,
                    session=session,
                    external_uri=uri,
                    entity_type="tag",
                    provider="diffbot",
                )
                if entity:
                    ContentEntity.get_or_create(
                        content_id=content.id,
                        entity_id=entity.id,
                        session=session,
                        origin="diffbot",
                        relevance_score=score * 100 if score <= 1 else score,
                        confidence=score if score <= 1 else score / 100.0,
                    )

    article.status = "enriching"
    return True


def ingest_article(session, raw_data: dict | EnrichedItemDTO):
    if isinstance(raw_data, dict):
        enriched_dto = EnrichedItemDTO(**raw_data)
    else:
        enriched_dto = raw_data

    cleaned_dto = normalize_article_data(enriched_dto)
    if not cleaned_dto:
        return None, "skipped"

    cleaned_dict = cleaned_dto.model_dump()
    return generic_ingest(
        session,
        object_type="article",
        raw_data=cleaned_dict,
        factory_func=create_article_model,
        update_func=update_article_model,
    )


# ---------------------------------------------------------------------------
# Video Ingestion
# ---------------------------------------------------------------------------


def _sync_video_comments(video_obj: Video, comments_data: list[dict]) -> bool:
    if not comments_data:
        return False

    changed = False
    existing_map = {c.external_id: c for c in video_obj.video_comments}

    for c_data in comments_data:
        ext_id = c_data["external_id"]
        if ext_id in existing_map:
            existing = existing_map[ext_id]
            if (
                existing.like_count != c_data["like_count"]
                or existing.reply_count != c_data["reply_count"]
                or existing.text != c_data["text"]
            ):
                existing.like_count = c_data["like_count"]
                existing.reply_count = c_data["reply_count"]
                existing.text = c_data["text"]
                existing.updated_at = c_data["updated_at"]
                changed = True
        else:
            new_comment = VideoComment(
                external_id=ext_id,
                author_name=c_data["author_name"],
                author_channel_id=c_data["author_channel_id"],
                text=c_data["text"],
                like_count=c_data["like_count"],
                reply_count=c_data["reply_count"],
                published_at=c_data["published_at"],
                updated_at=c_data["updated_at"],
            )
            video_obj.video_comments.append(new_comment)
            changed = True

    return changed


def create_video_model(data: dict) -> Video:
    if not data.get("external_id"):
        raise ValueError("Missing external_id for video")

    video = Video(
        title=data.get("title", "Untitled Video"),
        description=data.get("description", ""),
        external_id=data["external_id"],
        platform=data.get("platform", "youtube"),
        thumbnail_url=data.get("thumbnail_url"),
        channel_name=data.get("channel_name"),
        duration_seconds=data.get("duration_seconds"),
        url=data.get("url"),
    )
    _sync_video_comments(video, data.get("video_comments"))
    return video


def update_video_model(obj: Video, data: dict) -> bool:
    changed = False
    if data.get("duration_seconds") and obj.duration_seconds != data.get("duration_seconds"):
        obj.duration_seconds = data.get("duration_seconds")
        changed = True

    comments_changed = _sync_video_comments(obj, data.get("video_comments"))
    return changed or comments_changed


def ingest_video(session, raw_data: dict):
    cleaned = normalize_video_data(raw_data)
    if not cleaned:
        return None, "skipped"

    return generic_ingest(
        session,
        object_type="video",
        raw_data=cleaned,
        factory_func=create_video_model,
        update_func=update_video_model,
    )


# ---------------------------------------------------------------------------
# Post Ingestion
# ---------------------------------------------------------------------------


def create_post_model(data: dict) -> Post:
    return Post(
        title=data.get("title"),
        body=data.get("body"),
        external_id=data.get("external_id"),
        platform=data.get("platform", "reddit"),
        author=data.get("author"),
        subreddit=data.get("subreddit"),
        upvotes=data.get("upvotes", 0),
        comments_count=data.get("comments_count", 0),
    )


def ingest_post(session, raw_data: dict):
    cleaned = normalize_post_data(raw_data)
    if not cleaned:
        return None, "skipped"

    return generic_ingest(
        session,
        object_type="post",
        raw_data=cleaned,
        factory_func=create_post_model,
    )


# ---------------------------------------------------------------------------
# Unified Content Ingestion Dispatcher
# ---------------------------------------------------------------------------


def ingest_content(session, *, object_type: str, raw_data: dict):
    """Unified entry point for ingesting articles, videos, and posts."""
    if object_type == "article":
        return ingest_article(session, raw_data)
    elif object_type == "video":
        return ingest_video(session, raw_data)
    elif object_type == "post":
        return ingest_post(session, raw_data)
    return None
