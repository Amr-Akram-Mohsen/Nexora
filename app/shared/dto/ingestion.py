from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional

class RawItemDTO(BaseModel):
    """
    Data Transfer Object representing a raw item fetched from an external source.
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

class ClassifiedItemDTO(RawItemDTO):
    """
    Data Transfer Object representing an item after taxonomy and metadata classification.
    """
    section_slug: Optional[str] = None
    category_slug: Optional[str] = None
    topic_slugs: list[str] = Field(default_factory=list)
    brand_slugs: list[str] = Field(default_factory=list)
    facets: dict = Field(default_factory=dict)
    region: Optional[str] = None
    discovery_query: Optional[str] = None

class EnrichedItemDTO(ClassifiedItemDTO):
    """
    Data Transfer Object representing an item after content extraction and scoring.
    """
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    word_count: Optional[int] = 0
    quality_score: Optional[float] = 0.0
    is_content_scraped: Optional[bool] = False
    content_source: Optional[str] = None
    content: Optional[str] = None # legacy key for body/html

class ArticleCreateDTO(BaseModel):
    """
    Data Transfer Object representing validated, DB-ready article data.
    """
    model_config = ConfigDict(extra="allow") # Keep extra="allow" to pass through any extra metadata during migration

    title: str
    description: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    published_at: Any
    source_name: Optional[str] = None
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    word_count: Optional[int] = 0
    quality_score: Optional[float] = 0.0
    is_content_scraped: Optional[bool] = False
    content_source: Optional[str] = None
    content: Optional[str] = None # legacy key for body


