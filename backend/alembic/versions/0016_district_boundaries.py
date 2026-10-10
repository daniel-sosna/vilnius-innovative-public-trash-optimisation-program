"""Create the empty, explicitly imported district boundary catalog."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "district_boundaries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("district_name", sa.Text(), nullable=False),
        sa.Column("geometry", JSONB(), nullable=False),
        sa.Column("source_object_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("district_name", name="uq_district_boundaries_name"),
        sa.UniqueConstraint("source_object_id", name="uq_district_boundaries_source_id"),
    )


def downgrade() -> None:
    op.drop_table("district_boundaries")
