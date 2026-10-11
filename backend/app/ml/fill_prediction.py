import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from app.core.config import data_dir
from viptop_fill.csv_demo import predict_csv

MAX_FILL_LEVEL = 4
# The model is validated for "today" T in September 2026; it predicts T+1.
WINDOW_START = date(2026, 9, 1)
WINDOW_END = date(2026, 9, 30)
DAILY_PATTERN = "bin_days_*_enriched.csv"
REGISTRY_PATTERN = re.compile(r"bins_(\d+)\.csv")
POPULATION_FILE = "bin_population.csv"
MODEL_DIR = Path("ml") / "september-fill-predictor" / "product"
MODEL_FILES = ("model.joblib", "district_aliases.json")


def check_simulation_date(today: date) -> None:
    """Raise ValueError unless `today` is in the September 2026 simulation window."""
    if not WINDOW_START <= today <= WINDOW_END:
        raise ValueError(
            f"{today} is outside the simulation window: only September 2026 "
            f"({WINDOW_START}..{WINDOW_END}) is available for simulation"
        )


def _input_paths(directory: Path) -> tuple[Path, Path, Path, Path]:
    daily = sorted(directory.glob(DAILY_PATTERN))
    if len(daily) != 1:
        raise FileNotFoundError(
            "Historical data is not present in the system: expected exactly one "
            f"{DAILY_PATTERN} in {directory}, found {len(daily)}"
        )
    registries = sorted(
        (int(m.group(1)), path)
        for path in directory.iterdir()
        if (m := REGISTRY_PATTERN.fullmatch(path.name))
    )
    if not registries:
        raise FileNotFoundError(f"Bin registry export is not present: no bins_<digits>.csv in {directory}")
    population = directory / POPULATION_FILE
    if not population.is_file():
        raise FileNotFoundError(f"Population export is not present: {population}")
    model = directory / MODEL_DIR
    missing = [name for name in MODEL_FILES if not (model / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Fill prediction model is not present: {', '.join(missing)} missing in {model}")
    return daily[0], registries[-1][1], population, model


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=["", "NULL"])


def predict_fill_levels(day: date) -> dict[int, int]:
    """Return the predicted fill level of the bins the model covers on `day`.

    The contract the collection plan depends on: a dict `{bin_id: level}` with an integer
    level from 0 (empty) to 4 (full). Bins the model gives no level are absent.

    Levels come from the trained next-day model in `viptop_fill`, run live on the CSV
    exports in the data directory: it predicts `day` from history through `day - 1`, so
    `day - 1` must be in September 2026. History labels and the model's targets are
    synthetic assessments, not measured fill. A run scans the whole history CSV and takes
    about a minute. Inputs and the date are checked before the scan starts.
    """
    today = day - timedelta(days=1)
    check_simulation_date(today)
    daily, registry, population, model = _input_paths(data_dir())
    result = predict_csv(model, daily, _read_csv(registry), today.isoformat(), _read_csv(population))
    return {int(b): int(level) for b, level in zip(result.bin_id, result.fill_level)}
