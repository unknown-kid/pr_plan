"""add folders table and folder_id to papers

Revision ID: add_folders_table
Revises:
Create Date: 2026-02-17

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_folders_table"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    # Create folders table
    op.create_table(
        "folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_count", sa.Integer(), nullable=True, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["folders.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add folder_id to papers
    op.add_column(
        "papers", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_papers_folder_id", "papers", "folders", ["folder_id"], ["id"]
    )


def downgrade():
    op.drop_constraint("fk_papers_folder_id", "papers", type_="foreignkey")
    op.drop_column("papers", "folder_id")
    op.drop_table("folders")
