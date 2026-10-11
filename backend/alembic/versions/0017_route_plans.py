"""Add the stored route plan tables (route_plans, route_trucks, route_trips, route_stops)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "route_plans",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("waste_carrier", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("parameters", JSONB(), nullable=False),
        sa.Column("summary", JSONB(), nullable=False),
        sa.Column("unserved", JSONB(), nullable=False),
        sa.Column("excluded_trucks", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_route_plans"),
        sa.UniqueConstraint("date", "waste_carrier", name="uq_route_plans_date_carrier"),
    )
    # No foreign keys to trucks, landfills or sites: a plan keeps its own copies.
    op.create_table(
        "route_trucks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("truck_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("max_volume_m3", sa.Numeric(), nullable=False),
        sa.Column("landfill_id", sa.Integer(), nullable=False),
        sa.Column("landfill_name", sa.Text(), nullable=False),
        sa.Column("landfill_latitude", sa.Double(), nullable=False),
        sa.Column("landfill_longitude", sa.Double(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_route_trucks"),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["route_plans.id"], name="fk_route_trucks_plan_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_route_trucks_plan_id", "route_trucks", ["plan_id"])
    op.create_table(
        "route_trips",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("route_truck_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("load_m3", sa.Numeric(), nullable=False),
        sa.Column("distance_km", sa.Numeric(), nullable=False),
        sa.Column("duration_min", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_route_trips"),
        sa.ForeignKeyConstraint(
            ["route_truck_id"], ["route_trucks.id"], name="fk_route_trips_route_truck_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_route_trips_route_truck_id", "route_trips", ["route_truck_id"])
    op.create_table(
        "route_stops",
        sa.Column("trip_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.BigInteger(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("load_m3", sa.Numeric(), nullable=False),
        sa.Column("bin_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("trip_id", "seq", name="pk_route_stops"),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["route_trips.id"], name="fk_route_stops_trip_id", ondelete="CASCADE"
        ),
    )


def downgrade() -> None:
    op.drop_table("route_stops")
    op.drop_table("route_trips")
    op.drop_table("route_trucks")
    op.drop_table("route_plans")
