from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional


class RawItemDTO(BaseModel):
    """
    Data Transfer Object representing a raw product fetched from an external source.
    Allows extra fields to maintain backward compatibility with legacy dictionaries.
    """

    model_config = ConfigDict(extra="allow")

    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    external_id: Optional[str] = None
    platform: Optional[str] = None
    published_at: Optional[Any] = None
    image_url: Optional[str] = None

    # NEW — Event Registry first-class fields
    er_concepts: Optional[list] = None
    er_categories: Optional[list] = None
    er_event_uri: Optional[str] = None
    er_location: Optional[dict] = None
    er_source: Optional[dict] = None
    er_uri: Optional[str] = None   # canonical article URI
class ClassifiedItemDTO(RawItemDTO):
    """
    Data Transfer Object representing an product after taxonomy and metadata classification.
    """

    section_slug: Optional[str] = None
    category_slug: Optional[str] = None
    facets: dict = Field(default_factory=dict)
    region: Optional[str] = None
    discovery_query: Optional[str] = None


class EnrichedItemDTO(ClassifiedItemDTO):
    """
    Data Transfer Object representing an product after content extraction and scoring.
    """

    content_html: Optional[str] = None
    content_text: Optional[str] = None
    summary: Optional[str] = None
    word_count: Optional[int] = 0
    quality_score: Optional[float] = 0.0
    
    ingestion_method: Optional[str] = None
    language: Optional[str] = None
    sentiment_score: Optional[float] = None
    
    authors: Optional[list] = None
    extended_metadata: Optional[dict] = None
    images: Optional[list] = None
    videos: Optional[list] = None
    external_uri: Optional[str] = None
    
    # ER fields (promoted from extended_metadata)
    er_concepts: Optional[list] = None
    er_categories: Optional[list] = None
    er_event_uri: Optional[str] = None
    er_location: Optional[dict] = None
    er_source: Optional[dict] = None
    er_uri: Optional[str] = None

class ArticleCreateDTO(BaseModel):
    """
    Data Transfer Object representing validated, DB-ready article data.
    """

    model_config = ConfigDict(
        extra="allow"
    )  # Keep extra="allow" to pass through any extra metadata during migration

    title: str
    description: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    published_at: Any
    source_name: Optional[str] = None
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    summary: Optional[str] = None
    word_count: Optional[int] = 0
    quality_score: Optional[float] = 0.0
    
    ingestion_method: Optional[str] = None
    language: Optional[str] = None
    sentiment_score: Optional[float] = None
    
    authors: Optional[list] = None
    extended_metadata: Optional[dict] = None
    images: Optional[list] = None
    videos: Optional[list] = None
    external_uri: Optional[str] = None

    # Metadata preserved from Classification/Enrichment
    section_slug: Optional[str] = None
    category_slug: Optional[str] = None
    facets: dict = Field(default_factory=dict)
