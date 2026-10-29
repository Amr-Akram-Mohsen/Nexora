"""Add model columns missing from existing schema.

Revision ID: 7c1d9e3a8b20
Revises: 45ab2f905704
"""
from alembic import op
import sqlalchemy as sa


revision = "7c1d9e3a8b20"
down_revision = "45ab2f905704"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "article_categories",
        sa.Column("weight", sa.Float(), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column(
            "enrichment_priority",
            sa.Float(),
            server_default="0.0",
            nullable=False,
            comment="Priority score for enrichment worker. Calculated before enrichment.",
        ),
    )
    op.create_index(
        "ix_articles_enrichment_priority",
        "articles",
        ["enrichment_priority"],
        unique=False,
    )
    op.add_column(
        "products",
        sa.Column(
            "ingestion_status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_products_ingestion_status",
        "products",
        ["ingestion_status"],
        unique=False,
    )
    op.add_column(
        "products",
        sa.Column("scrape_status", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("scrape_errors", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_products_scrape_staleness",
        "products",
        ["scrape_status", "last_scraped_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_products_scrape_staleness", table_name="products")
    op.drop_column("products", "scrape_errors")
    op.drop_column("products", "last_scraped_at")
    op.drop_column("products", "scrape_status")
    op.drop_index("ix_products_ingestion_status", table_name="products")
    op.drop_column("products", "ingestion_status")
    op.drop_index("ix_articles_enrichment_priority", table_name="articles")
    op.drop_column("articles", "enrichment_priority")
    op.drop_column("article_categories", "weight")
