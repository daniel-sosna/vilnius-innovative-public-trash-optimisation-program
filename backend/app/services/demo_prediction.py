"""Real next-day inference with read-only database identity enrichment."""
from datetime import date, timedelta
from math import isfinite
from threading import Lock

from sqlalchemy import select

from app.infrastructure.models import Bin, Site
from app.interfaces.demo.schemas import PredictionResponse
from app.services.demo_prerequisites import validate_demo_paths


class DemoError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.status = code, status


inference_lock = Lock()


def mappable(row) -> bool:
    lat, lon = row["latitude"], row["longitude"]
    return (lat is not None and lon is not None and isfinite(lat) and isfinite(lon)
            and -90 <= lat <= 90 and -180 <= lon <= 180)


def stored_bins(session, ids: list[int]) -> list[dict]:
    return [dict(row) for row in session.execute(
        select(Bin.id.label("bin_id"), Bin.site_id, Bin.latitude, Bin.longitude,
               Site.address, Bin.waste_carrier)
        .join(Site, Site.id == Bin.site_id).where(Bin.id.in_(ids)).order_by(Bin.id)
    ).mappings()]


def predict(project_date: str, sessions) -> PredictionResponse:
    if not inference_lock.acquire(blocking=False):
        raise DemoError("inference_busy", "Prognozavimas jau vyksta. Palaukite ir bandykite dar kartą.", 409)
    try:
        paths = validate_demo_paths()
        # Optional inference dependencies never prevent ordinary API startup.
        import pandas as pd
        from viptop_fill.csv_demo import predict_csv

        registry = pd.read_csv(paths["registry"], keep_default_na=False, na_values=["", "NULL"])
        population = pd.read_csv(paths["population"], keep_default_na=False, na_values=["", "NULL"])
        ids = registry.id
        if ids.isna().any() or ids.duplicated().any() or not (ids > 0).all() or not (ids % 1 == 0).all():
            raise DemoError("registry_invalid", "Registro konteinerių ID turi būti teigiami ir unikalūs.")
        result = predict_csv(paths["product"], paths["daily"], registry, project_date, population)
        if (result.bin_id.duplicated().any() or set(result.bin_id) != set(ids)
                or not result.fill_level.isin(range(5)).all()):
            raise DemoError("prediction_invalid", "Prognozės neatitinka konteinerių registro.")
        # Open and close the transaction only after the expensive CSV scan.
        with sessions() as session:
            rows = stored_bins(session, [int(value) for value in ids])
        by_id = {row["bin_id"]: row for row in rows}
        if set(by_id) != set(ids) or any(by_id[int(row.id)]["site_id"] != row.site_id for row in registry.itertuples()):
            raise DemoError("registry_mismatch", "ML registras neatitinka duomenų bazės. Importuokite atitinkamus CSV eksportus.")
        bins = []
        for row in result.itertuples():
            if row.fill_level <= 2:
                continue
            item = dict(by_id[int(row.bin_id)], fill_level=int(row.fill_level))
            if not mappable(item):
                item.update(latitude=None, longitude=None)
            bins.append(item)
        return PredictionResponse(
            project_date=project_date,
            forecast_date=(date.fromisoformat(project_date) + timedelta(days=1)).isoformat(),
            evaluated_count=len(result), due_count=len(bins),
            unmappable_count=sum(not mappable(item) for item in bins), bins=bins,
        )
    finally:
        inference_lock.release()
