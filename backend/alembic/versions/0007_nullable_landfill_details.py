"""Allow unknown landfill details while retaining required identity and name.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# The two optional source URLs were already nullable in revision 0006.
RELAXED_COLUMNS = {
    "source_id": sa.Text(),
    "dataset_name": sa.Text(),
    "dataset_description": sa.Text(),
    "latitude": sa.Double(),
    "longitude": sa.Double(),
    "operator": sa.Text(),
    "address": sa.Text(),
    "facility_role": sa.Text(),
    "waste_streams": sa.ARRAY(sa.Text()),
    "status": sa.Text(),
    "coordinate_quality": sa.Text(),
    "coordinate_source": sa.Text(),
    "facility_source": sa.Text(),
    "verified_at": sa.Date(),
}


def upgrade() -> None:
    for column, column_type in RELAXED_COLUMNS.items():
        op.alter_column("landfills", column, existing_type=column_type, nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE landfills IN ACCESS EXCLUSIVE MODE"))
    missing_details = " OR ".join(f"{column} IS NULL" for column in RELAXED_COLUMNS)
    ids = connection.scalars(
        sa.text(f"SELECT id FROM landfills WHERE {missing_details} ORDER BY id")
    ).all()
    if ids:
        raise RuntimeError(
            "Landfill downgrade requires complete details; "
            f"found incomplete Landfill IDs: {', '.join(map(str, ids))}. "
            "Records and schema have not been changed. Supply the missing "
            "details deliberately before retrying."
        )
    for column, column_type in RELAXED_COLUMNS.items():
        op.alter_column("landfills", column, existing_type=column_type, nullable=False)
