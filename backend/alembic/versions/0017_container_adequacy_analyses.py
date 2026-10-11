"""Store imported monthly adequacy GeoJSON collections."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "container_adequacy_analyses",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("revision", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("analysis", JSONB(), nullable=False),
        sa.Column("features", JSONB(), nullable=False),
        sa.CheckConstraint("type = 'FeatureCollection'", name="ck_adequacy_collection_type"),
        sa.CheckConstraint("revision ~ '^[a-f0-9]{64}$'", name="ck_adequacy_revision"),
        sa.CheckConstraint(
            "jsonb_typeof(analysis) = 'object' AND "
            "analysis->>'id' IS NOT DISTINCT FROM id AND "
            "analysis->'complete' IS NOT DISTINCT FROM 'true'::jsonb",
            name="ck_adequacy_analysis",
        ),
        sa.CheckConstraint("jsonb_typeof(features) = 'array'", name="ck_adequacy_features"),
    )


def downgrade() -> None:
    op.drop_table("container_adequacy_analyses")
