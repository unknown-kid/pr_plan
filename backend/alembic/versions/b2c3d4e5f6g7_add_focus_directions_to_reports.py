"""add focus_directions to reading_reports

Revision ID: b2c3d4e5f6g7
Revises: add_folders_table
Create Date: 2026-02-24

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6g7"
down_revision = "add_folders_table"
branch_labels = None
depends_on = None


def upgrade():
    """Add focus_directions column to reading_reports table."""
    op.add_column(
        "reading_reports",
        sa.Column("focus_directions", sa.Text(), nullable=True),
    )


def downgrade():
    """Remove focus_directions column from reading_reports table."""
    op.drop_column("reading_reports", "focus_directions")
