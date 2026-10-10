"""Store imported waste collection service-zone polygons."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_zones",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("zone_name", sa.Text(), nullable=False),
        sa.Column("zone_number", sa.Integer(), nullable=False),
        sa.Column("geometry", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_service_zones"),
        sa.UniqueConstraint("zone_number", name="uq_service_zones_zone_number"),
        sa.CheckConstraint("btrim(zone_name) <> ''", name="ck_service_zones_name"),
        sa.CheckConstraint(
            "jsonb_typeof(geometry) = 'object' AND "
            "geometry->>'type' IS NOT DISTINCT FROM 'Polygon' AND "
            "jsonb_typeof(geometry->'coordinates') IS NOT DISTINCT FROM 'array'",
            name="ck_service_zones_geometry",
        ),
    )


def downgrade() -> None:
    op.drop_table("service_zones")
