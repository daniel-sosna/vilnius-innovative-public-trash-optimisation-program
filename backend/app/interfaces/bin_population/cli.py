import argparse
import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine
from app.interfaces.bin_population.allocation import (
    DEFAULT_SUPPRESSED_DENSITY,
    MAX_SUPPRESSED_DENSITY,
    Allocation,
    BinRecord,
    DensityFileError,
    PopulationPolygon,
    allocate,
    parse_polygons,
    percentile,
)

logger = logging.getLogger(__name__)

DEFAULT_FILE = Path(__file__).resolve().parents[3] / "data" / "population_density_1ha.geojson"

BINS_SQL = text(
    """
    SELECT id, waste_type, capacity_m3, latitude, longitude, object_group
    FROM bins ORDER BY id
    """
)


def suppressed_density(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--suppressed-density is not a number: {value!r}"
        ) from None
    if not 0 <= number <= MAX_SUPPRESSED_DENSITY:
        raise argparse.ArgumentTypeError(
            f"--suppressed-density must be between 0 and {MAX_SUPPRESSED_DENSITY}: {value!r}"
        )
    return number


def load_bins(connection) -> list[BinRecord]:
    return [
        BinRecord(
            id, waste_type,
            None if capacity is None else float(capacity),
            latitude, longitude, object_group,
        )
        for id, waste_type, capacity, latitude, longitude, object_group
        in connection.execute(BINS_SQL)
    ]


def rebuild(engine, polygons: list[PopulationPolygon]) -> Allocation:
    """Replace population_cells and bin_population in one transaction."""
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
        bins = load_bins(connection)
        allocation = allocate(bins, polygons)
        connection.execute(text("TRUNCATE bin_population, population_cells"))
        raw = connection.connection.driver_connection
        with raw.cursor() as cursor:
            with cursor.copy(
                "COPY population_cells (id, density_per_ha, suppressed, area_ha, residents, "
                "min_lon, min_lat, max_lon, max_lat, geometry) FROM STDIN"
            ) as copy:
                for p in polygons:
                    copy.write_row(
                        (p.id, p.density_per_ha, p.suppressed, p.area_ha, p.residents,
                         *p.bbox, json.dumps(p.rings))
                    )
            with cursor.copy(
                "COPY bin_population (bin_id, population_cell_id, resident_factor) FROM STDIN"
            ) as copy:
                for record in bins:
                    copy.write_row(
                        (record.id, allocation.cell_by_bin[record.id],
                         allocation.factor_by_bin[record.id])
                    )
    return allocation


def log_summary(polygons: list[PopulationPolygon], density: float, allocation: Allocation) -> None:
    suppressed = sum(p.suppressed for p in polygons)
    null = sum(p.density_per_ha is None and not p.suppressed for p in polygons)
    logger.info(
        "population_cells: %d polygons (%d suppressed, %d null), %.0f estimated residents; "
        "suppressed density used: %s per ha",
        len(polygons), suppressed, null, sum(p.residents for p in polygons), density,
    )
    with_polygon = sum(c is not None for c in allocation.cell_by_bin.values())
    logger.info(
        "bin_population: %d bins, %d with a polygon, %d without",
        len(allocation.cell_by_bin), with_polygon, len(allocation.cell_by_bin) - with_polygon,
    )
    for stats in allocation.stats.values():
        logger.info(
            "%s: %d residential bins at %d points; residents allocated %.0f, unallocated %.0f; "
            "distance p50/p90 %.0f/%.0f m; factor p50/p90/p99/max %.1f/%.1f/%.1f/%.1f",
            stats.waste_type, stats.residential_bins, stats.points,
            stats.allocated, stats.unallocated,
            percentile(stats.distances, 0.5), percentile(stats.distances, 0.9),
            percentile(stats.factors, 0.5), percentile(stats.factors, 0.9),
            percentile(stats.factors, 0.99), max(stats.factors, default=0.0),
        )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace population_cells and bin_population: load the population "
            "polygons and estimate the residents each bin serves."
        )
        parser.add_argument(
            "--file", type=Path, default=DEFAULT_FILE,
            help=f"Population density GeoJSON (default {DEFAULT_FILE})",
        )
        parser.add_argument(
            "--suppressed-density", type=suppressed_density,
            default=DEFAULT_SUPPRESSED_DENSITY,
            help='Assumed residents per ha for the suppressed value "<11" '
            f"(default {DEFAULT_SUPPRESSED_DENSITY}, 0-{MAX_SUPPRESSED_DENSITY})",
        )
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        polygons = parse_polygons(args.file, args.suppressed_density)
        engine = create_database_engine(Settings())
        allocation = rebuild(engine, polygons)
        log_summary(polygons, args.suppressed_density, allocation)
        return 0
    except Exception as error:
        cause = getattr(error, "orig", error)
        reason = (
            f"{type(cause).__name__}: {cause}"
            if isinstance(error, SQLAlchemyError)
            else str(error)
        )
        logger.error("Bin population rebuild failed, nothing was changed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
