"""Add minimal resident reports without changing existing collection records."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resident_requests",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("bin_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=False),
            server_default=sa.text("(statement_timestamp() AT TIME ZONE 'Europe/Vilnius')"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resident_requests"),
        sa.ForeignKeyConstraint(
            ["bin_id"], ["bins.id"],
            name="fk_resident_requests_bin_id", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_resident_requests_bin_id", "resident_requests", ["bin_id"])


def downgrade() -> None:
    op.drop_table("resident_requests")
