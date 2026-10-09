"""Add truck retirement and bounded site capacity.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels: None = None
depends_on: None = None

# Match Python str.strip whitespace, independent of PostgreSQL locale.
NONBLANK_NAME = r"btrim(name, U&'\0009\000a\000b\000c\000d\001c\001d\001e\001f\0020\0085\00a0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200a\2028\2029\202f\205f\3000') <> ''"


def upgrade() -> None:
    connection = op.get_bind()
    # Prevent another writer from invalidating preflight before checks are added.
    connection.execute(sa.text("LOCK TABLE trucks IN ACCESS EXCLUSIVE MODE"))
    invalid = connection.execute(
        sa.text(
            "SELECT id, max_bins_per_trip, name FROM trucks "
            "WHERE max_bins_per_trip NOT BETWEEN 1 AND 99 "
            f"OR NOT ({NONBLANK_NAME}) ORDER BY id"
        )
    ).all()
    if invalid:
        reasons = []
        for row in invalid:
            reason = []
            if not 1 <= row.max_bins_per_trip <= 99:
                reason.append("capacity outside 1–99")
            if not row.name.strip():
                reason.append("blank name")
            reasons.append(f"id={row.id}: {', '.join(reason) or 'blank name'}")
        raise RuntimeError(
            "Truck migration cannot continue; correct these records deliberately "
            "before retrying: " + "; ".join(reasons)
        )

    op.add_column(
        "trucks",
        sa.Column("deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.drop_constraint("ck_trucks_positive_capacity", "trucks", type_="check")
    op.create_check_constraint(
        "ck_trucks_capacity_range", "trucks", "max_bins_per_trip BETWEEN 1 AND 99"
    )
    op.create_check_constraint("ck_trucks_nonblank_name", "trucks", NONBLANK_NAME)
    op.create_check_constraint(
        "ck_trucks_deleted_unavailable", "trucks", "NOT deleted OR NOT available"
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE trucks IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM trucks WHERE deleted)")):
        raise RuntimeError(
            "Cannot downgrade while retired trucks exist: removing deleted would "
            "make them visible to the old application. Retain migration 0003."
        )
    op.drop_constraint("ck_trucks_deleted_unavailable", "trucks", type_="check")
    op.drop_constraint("ck_trucks_nonblank_name", "trucks", type_="check")
    op.drop_constraint("ck_trucks_capacity_range", "trucks", type_="check")
    op.create_check_constraint(
        "ck_trucks_positive_capacity", "trucks", "max_bins_per_trip > 0"
    )
    op.drop_column("trucks", "deleted")
