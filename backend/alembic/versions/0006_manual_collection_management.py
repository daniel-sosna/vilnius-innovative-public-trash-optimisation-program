"""Allow manual bins and cascade collection-site deletion without changing data."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def replace_site_foreign_key(action: str) -> None:
    op.drop_constraint("fk_bins_site_id", "bins", type_="foreignkey")
    op.create_foreign_key(
        "fk_bins_site_id", "bins", "sites", ["site_id"], ["id"], ondelete=action
    )


def upgrade() -> None:
    op.alter_column("bins", "external_id", existing_type=sa.BigInteger(), nullable=True)
    replace_site_foreign_key("CASCADE")


def downgrade() -> None:
    connection = op.get_bind()
    # Prevent insertion of a manual Bin between preflight and restoring NOT NULL.
    connection.execute(sa.text("LOCK TABLE bins IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM bins WHERE external_id IS NULL)")
    ):
        raise RuntimeError(
            "Cannot downgrade while manual Bins with NULL external IDs exist. "
            "Retain migration 0006; do not delete or invent external IDs for these records."
        )
    replace_site_foreign_key("RESTRICT")
    op.alter_column("bins", "external_id", existing_type=sa.BigInteger(), nullable=False)
