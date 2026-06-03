"""add comment content column

Revision ID: a8c2e4b91d72
Revises: 9f4d2a6b7c31
Create Date: 2026-06-02 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a8c2e4b91d72"
down_revision = "9f4d2a6b7c31"
branch_labels = None
depends_on = None


# def upgrade():
#     with op.batch_alter_table("comments", schema=None) as batch_op:
#         batch_op.add_column(sa.Column("content", sa.Text(), nullable=False, server_default=""))

# def upgrade():
#     with op.batch_alter_table("comments") as batch_op:
#         batch_op.add_column(
#             sa.Column("content", sa.Text(), nullable=True)
#         )

#     # optional: backfill if needed
#     op.execute("UPDATE comments SET content = '' WHERE content IS NULL")

#     with op.batch_alter_table("comments") as batch_op:
#         batch_op.alter_column(
#             "content",
#             nullable=False
#         )

def upgrade():
    op.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS content TEXT")
    op.execute("UPDATE comments SET content = '' WHERE content IS NULL")
    op.execute("ALTER TABLE comments ALTER COLUMN content SET NOT NULL")

def downgrade():
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_column("content")
