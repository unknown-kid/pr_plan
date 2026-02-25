"""add_embedding_model_to_papers

Revision ID: a1b2c3d4e5f6
Revises: 994c44f6a229
Create Date: 2026-02-17 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "994c44f6a229"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "papers",
        sa.Column("embedding_model_id", UUID(as_uuid=True), nullable=True),
        )
    op.add_column(
        "papers",
        sa.Column("embedding_model_name", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("papers", "embedding_model_name")
    op.drop_column("papers", "embedding_model_id")
