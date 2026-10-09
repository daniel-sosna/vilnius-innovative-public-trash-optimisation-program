"""Replace site-count truck capacity with volume and carrier.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels: None = None
depends_on: None = None

POSITIVE_FINITE_VOLUME = (
    "max_volume_m3 > 0 AND max_volume_m3 NOT IN "
    "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)"
)


def require_empty_trucks(operation: str, reason: str) -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE trucks IN ACCESS EXCLUSIVE MODE"))
    ids = connection.scalars(sa.text("SELECT id FROM trucks ORDER BY id")).all()
    if ids:
        raise RuntimeError(
            f"Truck {operation} requires an empty table, including retired trucks; "
            f"found IDs: {', '.join(map(str, ids))}. {reason} "
            "Records have not been changed. Resolve the incompatibility "
            "deliberately before retrying."
        )


def upgrade() -> None:
    require_empty_trucks(
        "volume upgrade",
        "Site counts cannot be converted to cubic metres and carriers are unknown.",
    )
    op.drop_constraint("ck_trucks_capacity_range", "trucks", type_="check")
    op.drop_column("trucks", "max_bins_per_trip")
    op.add_column("trucks", sa.Column("max_volume_m3", sa.Numeric(), nullable=False))
    op.add_column("trucks", sa.Column("waste_carrier", sa.Text(), nullable=False))
    op.create_check_constraint(
        "ck_trucks_positive_finite_volume", "trucks", POSITIVE_FINITE_VOLUME
    )


def downgrade() -> None:
    require_empty_trucks(
        "volume downgrade",
        "Volumes cannot be converted to site counts and carrier values would be lost.",
    )
    op.drop_constraint("ck_trucks_positive_finite_volume", "trucks", type_="check")
    op.drop_column("trucks", "waste_carrier")
    op.drop_column("trucks", "max_volume_m3")
    op.add_column("trucks", sa.Column("max_bins_per_trip", sa.Integer(), nullable=False))
    op.create_check_constraint(
        "ck_trucks_capacity_range", "trucks", "max_bins_per_trip BETWEEN 1 AND 99"
    )
