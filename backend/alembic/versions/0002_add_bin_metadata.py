"""Add optional collection-site metadata.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column("bins", sa.Column("type", sa.Text(), nullable=True))
    op.add_column("bins", sa.Column("greening", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bins", "greening")
    op.drop_column("bins", "type")
