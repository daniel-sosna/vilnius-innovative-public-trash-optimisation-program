"""Add planned collection dates per bin."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE bin_schedule (
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            bin_id BIGINT NOT NULL,
            date DATE NOT NULL,
            CONSTRAINT pk_bin_schedule PRIMARY KEY (id),
            CONSTRAINT uq_bin_schedule_bin_date UNIQUE (bin_id, date),
            CONSTRAINT fk_bin_schedule_bin_id FOREIGN KEY(bin_id) REFERENCES bins (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_bin_schedule_date ON bin_schedule (date)
        """
    )


def downgrade() -> None:
    op.drop_table("bin_schedule")
