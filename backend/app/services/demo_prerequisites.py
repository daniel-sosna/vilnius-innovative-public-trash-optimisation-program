"""Read-only checks that do not import model libraries during API startup."""
from pathlib import Path

from app.core.config import DemoSettings, data_dir


class DemoPrerequisiteError(ValueError):
    pass


def validate_demo_paths(settings: DemoSettings | None = None) -> dict[str, Path]:
    paths = (settings or DemoSettings()).paths()
    missing = []
    for prefix in ("sites", "bins", "bin_hist"):
        if not any(
            path.is_file() and path.stem.removeprefix(f"{prefix}_").isdigit()
            for path in data_dir().glob(f"{prefix}_*.csv")
        ):
            missing.append(str(data_dir() / f"{prefix}_<digits>.csv"))
    for name in ("daily", "registry", "population"):
        if not paths[name].is_file():
            missing.append(str(paths[name]))
    for name in ("model.joblib", "district_aliases.json"):
        if not (paths["product"] / name).is_file():
            missing.append(str(paths["product"] / name))
    if missing:
        raise DemoPrerequisiteError(
            "Trūksta demonstracijos duomenų: " + ", ".join(missing)
            + ". Pridėkite pateiktus failus arba nustatykite DEMO_*_PATH."
        )
    return paths
