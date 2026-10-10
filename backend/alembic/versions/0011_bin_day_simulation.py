"""Add simulated collection status and look-back features to bin_days."""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bin_days is derived and the new columns are NOT NULL: empty it, then rebuild.
    op.execute("TRUNCATE bin_days")
    op.execute(
        """
        ALTER TABLE bin_days
            ADD COLUMN collection_status TEXT NOT NULL,
            ADD COLUMN holidays_since_last_collection SMALLINT NOT NULL,
            ADD COLUMN collections_last_28d SMALLINT NOT NULL,
            ADD COLUMN missed_collections_28d SMALLINT NOT NULL,
            ADD CONSTRAINT ck_bin_days_collection_status CHECK (
                collection_status IN ('none', 'collected', 'retry_collected', 'failed', 'missed')
            ),
            ADD CONSTRAINT ck_bin_days_holidays_since_last_collection
                CHECK (holidays_since_last_collection >= 0),
            ADD CONSTRAINT ck_bin_days_collections_last_28d
                CHECK (collections_last_28d BETWEEN 0 AND 28),
            ADD CONSTRAINT ck_bin_days_missed_collections_28d
                CHECK (missed_collections_28d BETWEEN 0 AND 28)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE bin_days
            DROP COLUMN collection_status,
            DROP COLUMN holidays_since_last_collection,
            DROP COLUMN collections_last_28d,
            DROP COLUMN missed_collections_28d
        """
    )
