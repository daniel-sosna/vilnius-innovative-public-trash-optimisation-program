"""Replace legacy collection storage with physical VASA bins.

Old collection records are deliberately discarded; trucks are preserved.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Explicit drops reject unexpected external foreign keys.
    for name in ("service_events", "route_stops", "routes", "bins"):
        op.drop_table(name)
    op.execute(
        """
        CREATE TABLE sites (
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            site_key TEXT NOT NULL,
            address TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            CONSTRAINT pk_sites PRIMARY KEY (id),
            CONSTRAINT uq_sites_site_key UNIQUE (site_key),
            CONSTRAINT ck_sites_latitude_range CHECK (latitude BETWEEN -90 AND 90),
            CONSTRAINT ck_sites_longitude_range CHECK (longitude BETWEEN -180 AND 180)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE bins (
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            site_id BIGINT NOT NULL,
            external_id BIGINT NOT NULL,
            inventory_number TEXT,
            waste_type TEXT NOT NULL,
            capacity_m3 NUMERIC,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            district TEXT,
            region TEXT,
            sub_district TEXT,
            city TEXT,
            street TEXT,
            house_number TEXT,
            postal_code TEXT,
            territory_type TEXT,
            object_group TEXT,
            waste_carrier TEXT,
            client_count INTEGER,
            CONSTRAINT pk_bins PRIMARY KEY (id),
            CONSTRAINT uq_bins_external_id UNIQUE (external_id),
            CONSTRAINT ck_bins_latitude_range CHECK (latitude BETWEEN -90 AND 90),
            CONSTRAINT ck_bins_longitude_range CHECK (longitude BETWEEN -180 AND 180),
            CONSTRAINT ck_bins_client_count CHECK (client_count >= 0),
            CONSTRAINT fk_bins_site_id FOREIGN KEY(site_id) REFERENCES sites (id) ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_bins_site_id ON bins (site_id)
        """
    )
    op.execute(
        """
        CREATE TABLE bin_hist (
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            bin_id BIGINT NOT NULL,
            date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            was_serviced BOOLEAN NOT NULL,
            non_serviced_reason TEXT,
            fill_level SMALLINT,
            CONSTRAINT pk_bin_hist PRIMARY KEY (id),
            CONSTRAINT uq_bin_hist_event UNIQUE (bin_id, date, was_serviced),
            CONSTRAINT ck_bin_hist_fill_level CHECK (fill_level BETWEEN 0 AND 3),
            CONSTRAINT fk_bin_hist_bin_id FOREIGN KEY(bin_id) REFERENCES bins (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE vasa_import_runs (
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            scope_key TEXT NOT NULL,
            coverage JSONB NOT NULL,
            phase TEXT NOT NULL,
            diagnostics INTEGER DEFAULT 0 NOT NULL,
            CONSTRAINT pk_vasa_import_runs PRIMARY KEY (id),
            CONSTRAINT ck_vasa_import_runs_phase CHECK (phase IN ('tiles', 'history', 'finalize', 'complete'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_vasa_import_runs_scope ON vasa_import_runs (scope_key, id)
        """
    )
    op.execute(
        """
        CREATE TABLE vasa_import_progress (
            id BIGINT GENERATED ALWAYS AS IDENTITY,
            run_id BIGINT NOT NULL,
            kind TEXT NOT NULL,
            work_key TEXT NOT NULL,
            complete BOOLEAN NOT NULL,
            details JSONB NOT NULL,
            CONSTRAINT pk_vasa_import_progress PRIMARY KEY (id),
            CONSTRAINT uq_vasa_import_progress_work UNIQUE (run_id, kind, work_key),
            CONSTRAINT fk_vasa_import_progress_run_id FOREIGN KEY(run_id) REFERENCES vasa_import_runs (id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "Revision 0004 discards legacy collection records. Downgrade cannot "
        "restore them: restore a pre-upgrade backup or recreate disposable storage."
    )
