"""Add the derived bin-day calendar.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision: str = "0008"
down_revision: str = "0007"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE bin_days (
            bin_id BIGINT NOT NULL,
            date DATE NOT NULL,
            day_of_week SMALLINT NOT NULL,
            week_of_year SMALLINT NOT NULL,
            month SMALLINT NOT NULL,
            season SMALLINT NOT NULL,
            site_id BIGINT NOT NULL,
            waste_type TEXT NOT NULL,
            capacity_m3 NUMERIC,
            sub_district TEXT NOT NULL,
            object_group TEXT,
            CONSTRAINT pk_bin_days PRIMARY KEY (bin_id, date),
            CONSTRAINT ck_bin_days_day_of_week CHECK (day_of_week BETWEEN 1 AND 7),
            CONSTRAINT ck_bin_days_week_of_year CHECK (week_of_year BETWEEN 1 AND 53),
            CONSTRAINT ck_bin_days_month CHECK (month BETWEEN 1 AND 12),
            CONSTRAINT ck_bin_days_season CHECK (season BETWEEN 1 AND 4),
            CONSTRAINT fk_bin_days_bin_id FOREIGN KEY(bin_id) REFERENCES bins (id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    op.drop_table("bin_days")
