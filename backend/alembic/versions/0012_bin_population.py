"""Add population polygons, the per-bin resident allocation and its bin_days columns.

Revision ID: 0012
Revises: 0011
"""

from alembic import op

revision: str = "0012"
down_revision: str = "0011"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE population_cells (
            id INTEGER NOT NULL,
            density_per_ha INTEGER,
            suppressed BOOLEAN NOT NULL,
            area_ha DOUBLE PRECISION NOT NULL,
            residents DOUBLE PRECISION NOT NULL,
            min_lon DOUBLE PRECISION NOT NULL,
            min_lat DOUBLE PRECISION NOT NULL,
            max_lon DOUBLE PRECISION NOT NULL,
            max_lat DOUBLE PRECISION NOT NULL,
            geometry JSONB NOT NULL,
            CONSTRAINT pk_population_cells PRIMARY KEY (id),
            CONSTRAINT ck_population_cells_residents CHECK (residents >= 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE bin_population (
            bin_id BIGINT NOT NULL,
            population_cell_id INTEGER,
            resident_factor DOUBLE PRECISION NOT NULL,
            CONSTRAINT pk_bin_population PRIMARY KEY (bin_id),
            CONSTRAINT ck_bin_population_resident_factor CHECK (resident_factor >= 0),
            CONSTRAINT fk_bin_population_bin_id FOREIGN KEY (bin_id)
                REFERENCES bins (id) ON DELETE CASCADE,
            CONSTRAINT fk_bin_population_population_cell_id FOREIGN KEY (population_cell_id)
                REFERENCES population_cells (id) ON DELETE RESTRICT
        )
        """
    )
    # bin_days is derived and the new column is NOT NULL: empty it, then rebuild.
    op.execute("TRUNCATE bin_days")
    op.execute(
        """
        ALTER TABLE bin_days
            ADD COLUMN population_cell_id INTEGER,
            ADD COLUMN resident_factor DOUBLE PRECISION NOT NULL,
            ADD CONSTRAINT ck_bin_days_resident_factor CHECK (resident_factor >= 0)
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE bin_days DROP COLUMN population_cell_id, DROP COLUMN resident_factor"
    )
    op.drop_table("bin_population")
    op.drop_table("population_cells")
