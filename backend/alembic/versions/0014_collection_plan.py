"""Add the daily collection plan tables (collection_stops, stop_bins)."""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_stops",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("waste_carrier", sa.Text(), nullable=True),
        sa.Column("site_id", sa.BigInteger(), nullable=False),
        sa.Column("overall_volume_m3", sa.Numeric(), nullable=False),
        sa.Column("overall_predicted_fill_m3", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_collection_stops"),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name="fk_collection_stops_site_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "date",
            "waste_carrier",
            "site_id",
            name="uq_collection_stops_date_carrier_site",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("ix_collection_stops_date", "collection_stops", ["date"])
    op.create_table(
        "stop_bins",
        sa.Column("stop_id", sa.BigInteger(), nullable=False),
        sa.Column("bin_id", sa.BigInteger(), nullable=False),
        sa.Column("predicted_fill", sa.SmallInteger(), nullable=False),
        sa.Column("due", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("stop_id", "bin_id", name="pk_stop_bins"),
        sa.ForeignKeyConstraint(
            ["stop_id"], ["collection_stops.id"], name="fk_stop_bins_stop_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["bin_id"], ["bins.id"], name="fk_stop_bins_bin_id", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "predicted_fill BETWEEN 0 AND 4", name="ck_stop_bins_predicted_fill_range"
        ),
    )
    op.create_index("ix_stop_bins_bin_id", "stop_bins", ["bin_id"])


def downgrade() -> None:
    op.drop_table("stop_bins")
    op.drop_table("collection_stops")
