"""add share interactions

Revision ID: 9f4d2a6b7c31
Revises: 674cdff6ac86
Create Date: 2026-06-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "9f4d2a6b7c31"
down_revision = "674cdff6ac86"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("target_type IN ('content', 'item')", name="ck_share_target_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_share_target", "shares", ["target_type", "target_id"], unique=False)
    op.create_index("ix_share_user_created", "shares", ["user_id", "created_at"], unique=False)


def downgrade():
    op.drop_index("ix_share_user_created", table_name="shares")
    op.drop_index("ix_share_target", table_name="shares")
    op.drop_table("shares")
