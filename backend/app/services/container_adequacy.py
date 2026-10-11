"""Reproducible residential catchment analysis; no database or network access."""
from dataclasses import asdict, dataclass, field
import csv
from math import isfinite
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import os
import tempfile

from app.services.adequacy_artifacts import WASTE_TYPES, fingerprint, month_bounds, validate_artifact

from app.interfaces.bin_population.allocation import (
    BinRecord, allocate, parse_polygons, percentile,
)

SCHEMA_VERSION = "1"
METHOD_VERSION = "1"


@dataclass(frozen=True)
class Policy:
    pressure_quantile: float = 0.80
    access_distance_m: float = 300.0
    min_assessments: int = 5
    min_assessed_days: int = 3
    min_bin_coverage: float = 0.50
    excess_rate: float = 0.05
    exceedance_probability: float = 0.90
    suppressed_density: float = 5.0

    def __post_init__(self):
        for name in ("pressure_quantile", "min_bin_coverage", "excess_rate", "exceedance_probability"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if not isfinite(self.access_distance_m) or self.access_distance_m <= 0:
            raise ValueError("access_distance_m must be positive and finite")
        if self.min_assessments < 1 or self.min_assessed_days < 1:
            raise ValueError("Assessment and day minimums must be positive")
        if not 0 <= self.suppressed_density <= 10:
            raise ValueError("suppressed_density must be between 0 and 10")


def latest_export(directory: Path, table: str) -> Path:
    import re
    matches = [(int(m.group(1)), p) for p in directory.glob(f"{table}_*.csv")
               if (m := re.fullmatch(rf"{table}_(\d+)\.csv", p.name))]
    if not matches:
        raise ValueError(f"Missing required export: {directory / (table + '_<digits>.csv')}")
    return max(matches)[1]


def load_registry(path: Path) -> tuple[list[BinRecord], dict[int, dict]]:
    records, raw = [], {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"id", "site_id", "latitude", "longitude", "capacity_m3", "waste_type", "object_group"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Registry missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            identity = int(row["id"])
            if identity in raw:
                raise ValueError(f"Duplicate registry bin {identity}")
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if not isfinite(lat) or not isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError(f"Invalid coordinates for bin {identity}")
            capacity = None if row["capacity_m3"] in ("", "NULL") else float(row["capacity_m3"])
            if capacity is not None and not isfinite(capacity):
                raise ValueError(f"Invalid capacity for bin {identity}")
            records.append(BinRecord(identity, row["waste_type"], capacity, lat, lon,
                                     None if row["object_group"] in ("", "NULL") else row["object_group"]))
            raw[identity] = row
    if not records:
        raise ValueError("Registry contains no bins")
    return records, raw


def build_snapshot(bins: list[BinRecord], population_path: Path, policy: Policy) -> dict:
    polygons = parse_polygons(population_path, policy.suppressed_density)
    allocation = allocate(bins, polygons)
    thresholds = {}
    bin_to_point = {}
    for waste_type in WASTE_TYPES:
        points = allocation.points_by_type.get(waste_type, [])
        pressures = [p.residents / p.capacity for p in points if p.residents > 0]
        thresholds[waste_type] = percentile(pressures, policy.pressure_quantile) if pressures else None
        for point in points:
            for record in point.bins:
                bin_to_point[record.id] = (waste_type, point.min_bin_id)
    areas = []
    for polygon in sorted(polygons, key=lambda p: p.id):
        known = polygon.density_per_ha is not None or polygon.suppressed
        residents = polygon.residents if known else None
        for code, waste_type in enumerate(WASTE_TYPES, 1):
            key = polygon.id, waste_type
            point = allocation.point_by_area.get(key)
            distance = allocation.distance_by_area.get(key)
            pressure = point.residents / point.capacity if point else None
            reasons = []
            if not known:
                reasons.append("unknown_population")
            elif residents == 0:
                reasons.append("no_resident_demand")
            elif not point:
                reasons.append("no_serving_point")
            high_pressure = pressure is not None and pressure >= thresholds[waste_type]
            long_access = distance is not None and distance > policy.access_distance_m
            if high_pressure:
                reasons.append("high_pressure")
            if long_access:
                reasons.append("long_access")
            areas.append({"type": "Feature", "id": polygon.id * 10 + code,
                          "geometry": {"type": "Polygon", "coordinates": polygon.rings},
                          "properties": {
                              "population_cell_id": polygon.id, "waste_type": waste_type,
                              "residents": residents, "suppressed": polygon.suppressed,
                              "area_ha": polygon.area_ha, "population_known": known,
                              "point_id": point.min_bin_id if point else None,
                              "attributed_capacity_m3": point.capacity * residents / point.residents if point else 0.0 if known else None,
                              "point_capacity_m3": point.capacity if point else None,
                              "point_residents": point.residents if point else None,
                              "point_bin_count": len(point.bins) if point else 0,
                              "pressure": pressure, "distance_m": distance,
                              "high_pressure": high_pressure, "long_access": long_access,
                              "reasons": reasons,
                          }})
    return {"areas": areas, "allocation": allocation, "bin_to_point": bin_to_point,
            "thresholds": thresholds, "policy": asdict(policy), "polygons": polygons}


@dataclass
class Assessments:
    total: int = 0
    level4: int = 0
    days: int = 0  # A compact calendar bitmask.
    bins: set[int] = field(default_factory=set)


def aggregate_daily(path: Path, registry: dict[int, dict], bin_to_point: dict) -> dict:
    counts = defaultdict(Assessments)
    calendars = defaultdict(dict)
    cohort, total_rows = set(), 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"bin_id", "date", "waste_type", "capacity_m3", "object_group", "site_id", "fill_level"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Fill CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for line, row in enumerate(reader, 2):
            identity = int(row["bin_id"])
            if identity not in registry:
                raise ValueError(f"Fill CSV line {line}: unknown bin {identity}")
            day = date.fromisoformat(row["date"])
            month = day.strftime("%Y-%m")
            flag = 1 << (day.day - 1)
            previous = calendars[month].get(identity, 0)
            if previous & flag:
                raise ValueError(f"Duplicate bin/day: {identity}/{day}")
            calendars[month][identity] = previous | flag
            cohort.add(identity)
            total_rows += 1
            source = registry[identity]
            for key in ("waste_type", "object_group", "site_id"):
                if row[key] not in (source[key], "" if source[key] == "NULL" else source[key]):
                    raise ValueError(f"Fill CSV line {line}: {key} disagrees with registry bin {identity}")
            def capacity(value):
                return None if value in ("", "NULL") else float(value)
            if capacity(row["capacity_m3"]) != capacity(source["capacity_m3"]):
                raise ValueError(f"Fill CSV line {line}: capacity disagrees with registry bin {identity}")
            label = row["fill_level"]
            if label not in ("", "NULL", "0", "1", "2", "3", "4"):
                raise ValueError(f"Fill CSV line {line}: invalid fill level {label!r}")
            if label not in ("", "NULL") and identity in bin_to_point:
                waste_type, point_id = bin_to_point[identity]
                item = counts[(month, waste_type, point_id)]
                item.total += 1
                item.level4 += int(label == "4")
                item.days |= flag
                item.bins.add(identity)
    if not cohort:
        raise ValueError("Fill CSV has no daily rows")
    complete, coverage = [], {}
    for month, masks in sorted(calendars.items()):
        _, last = month_bounds(month)
        full = (1 << last.day) - 1
        covered = sum(mask == full for mask in masks.values())
        coverage[month] = {"cohort_bins": len(cohort), "bins_present": len(masks), "bins_with_full_calendar": covered,
                           "complete": covered == len(cohort), "calendar_rows": sum(m.bit_count() for m in masks.values())}
        if covered == len(cohort):
            complete.append(month)
    return {"counts": counts, "complete_months": complete, "coverage": coverage,
            "cohort_bins": len(cohort), "excluded_bins": sorted(set(registry) - cohort), "rows": total_rows}


def fit_assessments(items: dict[int, Assessments], bin_counts: dict[int, int], policy: Policy) -> tuple[dict, dict | None]:
    import numpy as np
    from scipy.optimize import minimize
    from scipy.special import betaln, expit, logit
    from scipy.stats import beta

    assessed = {key: item for key, item in items.items() if item.total}
    if not assessed:
        return {}, None
    n = np.array([x.total for x in assessed.values()], dtype=float)
    y = np.array([x.level4 for x in assessed.values()], dtype=float)
    def objective(parameters):
        mu, k = expit(parameters[0]), np.exp(parameters[1])
        a, b = mu * k, (1 - mu) * k
        return float(-np.sum(betaln(y + a, n - y + b) - betaln(a, b)))
    initial = np.clip(y.sum() / n.sum(), 1e-6, 1 - 1e-6)
    result = minimize(objective, [logit(initial), np.log(10)], method="L-BFGS-B",
                      bounds=[(logit(1e-6), logit(1 - 1e-6)), (np.log(.1), np.log(1000))])
    if not result.success or not np.isfinite(result.fun):
        raise ValueError(f"Beta-binomial fit did not converge: {result.message}")
    mu, k = float(expit(result.x[0])), float(np.exp(result.x[1]))
    alpha, beta_prior = mu * k, (1 - mu) * k
    prior = {"alpha": alpha, "beta": beta_prior, "mean": mu, "concentration": k,
             "points": len(assessed), "converged": True, "objective": float(result.fun)}
    estimates = {}
    for point_id, item in assessed.items():
        a, b = item.level4 + alpha, item.total - item.level4 + beta_prior
        low, high = beta.ppf([.05, .95], a, b)
        exceedance = float(beta.sf(mu + policy.excess_rate, a, b)) if mu + policy.excess_rate < 1 else 0.0
        coverage = len(item.bins) / bin_counts[point_id]
        sufficient = (item.total >= policy.min_assessments and item.days.bit_count() >= policy.min_assessed_days
                      and coverage >= policy.min_bin_coverage)
        estimates[point_id] = {"assessments": item.total, "level4_count": item.level4,
                               "assessed_days": item.days.bit_count(), "assessed_bins": len(item.bins),
                               "bin_coverage": coverage, "raw_frequency": item.level4 / item.total,
                               "smoothed_frequency": a / (a + b), "interval_low": float(low), "interval_high": float(high),
                               "exceedance_probability": exceedance, "sufficient_evidence": sufficient,
                               "elevated_fill": sufficient and exceedance >= policy.exceedance_probability}
    return estimates, prior


def classify(properties: dict, policy: Policy) -> tuple[str, list[str]]:
    reasons = [r for r in properties["reasons"] if r in ("unknown_population", "no_resident_demand", "no_serving_point")]
    high = properties["pressure"] is not None and properties["high_pressure"]
    long_access = properties["distance_m"] is not None and properties["distance_m"] > policy.access_distance_m
    if high:
        reasons.append("high_pressure")
    if long_access:
        reasons.append("long_access")
    if any(r in reasons for r in ("unknown_population", "no_resident_demand", "no_serving_point")):
        return "unavailable", reasons
    if not properties["sufficient_evidence"]:
        return "insufficient_evidence", reasons + ["insufficient_fill_evidence"]
    elevated = properties["exceedance_probability"] >= policy.exceedance_probability
    if elevated:
        reasons.append("elevated_level4")
    pressure = high or long_access
    category = ("priority_shortage" if pressure and elevated else "potential_shortage" if pressure
                else "overflow_without_pressure" if elevated else "ordinary")
    return category, reasons


def make_document(snapshot: dict, daily: dict, month: str, source_hashes: dict, policy: Policy) -> dict:
    if month not in daily["complete_months"]:
        raise ValueError(f"{month} has no complete daily calendar for the source cohort")
    start, end = month_bounds(month)
    priors, estimates, point_summaries = {}, {}, {}
    for waste_type in WASTE_TYPES:
        points = snapshot["allocation"].points_by_type.get(waste_type, [])
        items = {p.min_bin_id: daily["counts"].get((month, waste_type, p.min_bin_id), Assessments()) for p in points}
        estimated, prior = fit_assessments(items, {p.min_bin_id: len(p.bins) for p in points}, policy)
        estimates[waste_type], priors[waste_type] = estimated, prior
        point_summaries[waste_type] = {"points": len(points), "assessed_points": len(estimated),
                                      "assessments": sum(x.total for x in items.values()),
                                      "level4_count": sum(x.level4 for x in items.values())}
    empty = {"assessments": 0, "level4_count": 0, "assessed_days": 0, "assessed_bins": 0,
             "bin_coverage": 0.0, "raw_frequency": None, "smoothed_frequency": None,
             "interval_low": None, "interval_high": None, "exceedance_probability": None,
             "sufficient_evidence": False}
    features = []
    for area in snapshot["areas"]:
        properties = dict(area["properties"])
        properties.update(estimates[properties["waste_type"]].get(properties["point_id"], empty))
        properties.pop("elevated_fill", None)
        properties["category"], properties["reasons"] = classify(properties, policy)
        features.append({**area, "properties": properties})
    policy_values = asdict(policy)
    identity = {"sources": source_hashes, "policy": policy_values, "method": METHOD_VERSION, "schema": SCHEMA_VERSION, "month": month}
    return {"type": "FeatureCollection", "analysis": {
        "id": f"adequacy-{month}", "month": month, "period_start": start.isoformat(), "period_end": end.isoformat(),
        "complete": True, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION,
        "fill_provenance": "synthetic", "source_fingerprints": source_hashes,
        "input_fingerprint": fingerprint(identity), "policy": policy_values,
        "pressure_thresholds": snapshot["thresholds"], "priors": priors,
        "quality": {"calendar": daily["coverage"][month], "excluded_registry_bins": daily["excluded_bins"],
                    "point_summaries": point_summaries,
                    "category_counts": dict(Counter(f["properties"]["category"] for f in features))},
        "assumptions": ["Declared residents and registry are static snapshots, not live presence or historical inventory.",
                        "Nearest residential point by straight-line centroid distance; access eligibility is assumed.",
                        "Capacity values are assumed to be cubic metres; attributed capacity is not capacity physically inside the area.",
                        f"Suppressed population density uses {policy.suppressed_density:g} residents/ha.",
                        "Synthetic fill assessments depend on resident pressure and occur primarily before successful synthetic collections.",
                        "Associations are scenario results, not independent evidence of real-world shortage, overflow duration or causality.",
                        "Posterior intervals are conditional on the model; correlated assessments and shared point evidence are not independent events."],
    }, "features": features}


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish(document: dict, directory: Path, regenerate=False) -> tuple[Path, str]:
    validate_artifact(document)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"adequacy_{document['analysis']['month']}.geojson"
    if path.exists():
        existing = validate_artifact(json.loads(path.read_text(encoding="utf-8")))
        if existing["analysis"]["input_fingerprint"] == document["analysis"]["input_fingerprint"]:
            return path, "reused"
        if not regenerate:
            raise ValueError(f"{path.name}: inputs/method changed; use --regenerate for explicit replacement")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         suffix=".tmp", delete=False, newline="\n") as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        validate_artifact(json.loads(temporary.read_text(encoding="utf-8")))
        os.replace(temporary, path)
        return path, "generated"
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
