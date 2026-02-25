"""add_chunk_counts_to_papers

Revision ID: 994c44f6a229
Revises: 6e3528f8ff2a
Create Date: 2026-02-17 01:55:47.352177

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "994c44f6a229"
down_revision: Union[str, Sequence[str], None] = "6e3528f8ff2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "papers",
        sa.Column("total_chunks", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "papers",
        sa.Column("processed_chunks", sa.Integer(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("papers", "processed_chunks")
    op.drop_column("papers", "total_chunks")
