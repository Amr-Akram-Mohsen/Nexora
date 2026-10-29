"""Add model tables missing from the initial schema.

Revision ID: 45ab2f905704
Revises: 0a3a9baa1c62
"""
from alembic import op
import sqlalchemy as sa


revision = "45ab2f905704"
down_revision = "0a3a9baa1c62"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("uri", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=True),
        sa.Column("is_agency", sa.Boolean(), nullable=False),
        sa.Column("icon_url", sa.Text(), nullable=True),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_authors_name", "authors", ["name"], unique=False)
    op.create_index("ix_authors_slug", "authors", ["slug"], unique=True)

    op.create_table(
        "article_authors",
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"]),
        sa.PrimaryKeyConstraint("article_id", "author_id"),
    )
    op.create_index(
        "ix_article_authors_article", "article_authors", ["article_id"], unique=False
    )
    op.create_index(
        "ix_article_authors_author", "article_authors", ["author_id"], unique=False
    )

    op.create_table(
        "video_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("author_name", sa.String(length=150), nullable=True),
        sa.Column("author_channel_id", sa.String(length=100), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_video_comments_external_id",
        "video_comments",
        ["external_id"],
        unique=True,
    )
    op.create_index(
        "ix_video_comments_published_at",
        "video_comments",
        ["published_at"],
        unique=False,
    )

    op.create_table(
        "product_discovery_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("store_slug", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=True),
        sa.Column("category_path", sa.String(length=500), nullable=True),
        sa.Column("subcategory", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("discovered_at", sa.DateTime(), nullable=False),
        sa.Column("last_attempted_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_url"),
    )
    op.create_index(
        "ix_discovery_queue_discovered",
        "product_discovery_queue",
        ["discovered_at"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_queue_status",
        "product_discovery_queue",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_queue_store_status",
        "product_discovery_queue",
        ["store_slug", "status"],
        unique=False,
    )


def downgrade():
    op.drop_table("product_discovery_queue")
    op.drop_table("video_comments")
    op.drop_table("article_authors")
    op.drop_table("authors")
