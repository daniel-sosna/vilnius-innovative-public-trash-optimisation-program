import argparse
import csv
import logging
import re
from pathlib import Path

from psycopg import sql
from psycopg.errors import FeatureNotSupported
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.core.config import Settings, data_dir
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine
from app.infrastructure.models import Base

logger = logging.getLogger(__name__)

COLLECTION_TABLES = {"sites", "bins", "bin_hist"}
SYNC_STATE_TABLES = ("vasa_import_runs", "vasa_import_progress")
# Tables derived from bins, emptied when bins are replaced without their own file,
# with the command that refills each.
BIN_DERIVED_TABLES = {
    "bin_days": "python -m app.interfaces.bin_days --start YYYY-MM-DD --end YYYY-MM-DD",
    "bin_population": "python -m app.interfaces.bin_population",
    "bin_schedule": "python -m app.interfaces.bin_schedule_sync",
}
# Tables referencing bins that cannot be refilled; their rows belong to the replaced bins.
BIN_DEPENDENT_TABLES = ("resident_requests",)
COPY_CHUNK_BYTES = 1 << 16


def discover_files(directory: Path) -> dict[str, Path]:
    """Return the newest `<table>_<digits>.csv` per schema table, parents first."""
    csv_files = sorted(directory.glob("*.csv"))
    selected: dict[str, Path] = {}
    matched: set[Path] = set()
    for table in Base.metadata.sorted_tables:
        pattern = re.compile(rf"^{re.escape(table.name)}_(\d+)\.csv$")
        candidates = [
            (match.group(1), path)
            for path in csv_files
            if (match := pattern.match(path.name))
        ]
        matched.update(path for _, path in candidates)
        if candidates:
            selected[table.name] = max(candidates)[1]
    for path in csv_files:
        if path not in matched:
            logger.warning("Ignoring %s: it does not match any table", path.name)
    return selected


def read_columns(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as file:
        header = next(csv.reader(file), None)
    if not header:
        raise ValueError(f"{path.name} has no header row")
    return header


def emptied_derived_tables(files: dict[str, Path]) -> list[str]:
    if "bins" not in files:
        return []
    return [
        name
        for name in (*BIN_DERIVED_TABLES, *BIN_DEPENDENT_TABLES)
        if name not in files
    ]


def load_tables(engine, files: dict[str, Path]) -> dict[str, int]:
    columns = {table: read_columns(path) for table, path in files.items()}
    truncated = list(files)
    if COLLECTION_TABLES & files.keys():
        truncated += [name for name in SYNC_STATE_TABLES if name not in files]
    truncated += emptied_derived_tables(files)
    counts: dict[str, int] = {}
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
        cursor = connection.connection.dbapi_connection.cursor()
        cursor.execute(
            sql.SQL("TRUNCATE {}").format(
                sql.SQL(", ").join(sql.Identifier(name) for name in truncated)
            )
        )
        for table, path in files.items():
            statement = sql.SQL(
                "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL 'NULL')"
            ).format(
                sql.Identifier(table),
                sql.SQL(", ").join(sql.Identifier(column) for column in columns[table]),
            )
            with cursor.copy(statement) as copy, path.open("rb") as file:
                while chunk := file.read(COPY_CHUNK_BYTES):
                    copy.write(chunk)
        for table in files:
            cursor.execute(
                sql.SQL(
                    "SELECT setval(pg_get_serial_sequence({name}, 'id'),"
                    " COALESCE(MAX(id), 0) + 1, false) FROM {table}"
                ).format(name=sql.Literal(table), table=sql.Identifier(table))
            )
        for table in files:
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            )
            counts[table] = cursor.fetchone()[0]
    return counts


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace database tables with CSV exports named <table>_<digits>.csv (newest wins)."
        )
        parser.add_argument(
            "--dir",
            type=Path,
            default=data_dir(),
            help="Directory with CSV exports (default: VIPTOP_DATA_DIR, else backend/data)",
        )
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        if not args.dir.is_dir():
            logger.error("Table import failed: directory %s does not exist", args.dir)
            return 1
        files = discover_files(args.dir)
        if not files:
            logger.error(
                "Nothing to import: no <table>_<digits>.csv files in %s", args.dir
            )
            return 1
        engine = create_database_engine(Settings())
        counts = load_tables(engine, files)
        for table, path in files.items():
            logger.info("%s <- %s: %d rows", table, path.name, counts[table])
        for table in emptied_derived_tables(files):
            if table in BIN_DERIVED_TABLES:
                logger.info(
                    "%s emptied with the replaced bins; refill it with %s",
                    table,
                    BIN_DERIVED_TABLES[table],
                )
            else:
                logger.info("%s emptied with the replaced bins", table)
        return 0
    except Exception as error:
        cause = getattr(error, "orig", error)
        reason = (
            f"{type(cause).__name__}: {cause}"
            if isinstance(error, SQLAlchemyError)
            else str(error)
        )
        logger.error("Table import failed, nothing was changed: %s", reason)
        if isinstance(cause, FeatureNotSupported):
            logger.error(
                "A table being replaced is referenced by a table without a file; "
                "files for the referencing tables are also required"
            )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
