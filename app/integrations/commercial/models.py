"""
Commercial Integration Support Models.

This module defines integration-specific database models that do not belong
in the core product domain (app/domains/product/models.py).

ProductDiscoveryQueue tracks URLs discovered by scrapers/search/categories
before they are processed, allowing deduplication across runs, persistent queueing,
and scraping status tracking.
"""
from __future__ import annotations

from datetime import datetime, timezone
from app.core.extensions import db


class ProductDiscoveryQueue(db.Model):
    """
    Queue table for discovered product URLs across commercial integration sources.
    
    Status lifecycle:
      pending → scraping → scraped → inserted | duplicate | failed | skipped
    """
    __tablename__ = "product_discovery_queue"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    normalized_url = db.Column(db.Text, nullable=False, unique=True)
    store_slug = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(50))  # "category" | "search" | "manual" | "newsletter"
    keyword = db.Column(db.String(255), nullable=True)
    category_path = db.Column(db.String(500), nullable=True)
    subcategory = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="pending")
    discovered_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_attempted_at = db.Column(db.DateTime, nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    raw_metadata = db.Column(db.JSON, nullable=True)

    __table_args__ = (
        db.Index("ix_discovery_queue_status", "status"),
        db.Index("ix_discovery_queue_store_status", "store_slug", "status"),
        db.Index("ix_discovery_queue_discovered", "discovered_at"),
    )

    def __repr__(self) -> str:
        return f"<ProductDiscoveryQueue id={self.id} status='{self.status}' url='{self.normalized_url}'>"
