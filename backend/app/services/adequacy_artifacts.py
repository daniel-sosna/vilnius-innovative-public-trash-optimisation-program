"""Read/validate portable adequacy artifacts without analysis or database dependencies."""
import calendar
from collections import Counter
from datetime import date
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

WASTE_TYPES = ("Mixed municipal waste", "Paper/plastic waste", "Glass waste")
CATEGORIES = {"unavailable", "insufficient_evidence", "priority_shortage", "potential_shortage",
              "overflow_without_pressure", "ordinary"}
ARTIFACT_PATTERN = re.compile(r"adequacy_(\d{4}-\d{2})\.geojson")


def month_bounds(month: str) -> tuple[date, date]:
    start = date.fromisoformat(month + "-01")
    return start, start.replace(day=calendar.monthrange(start.year, start.month)[1])


def output_directory(directory: Path) -> Path:
    return directory / "analyses" / "container-adequacy"


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_artifact(document: dict) -> dict:
    def require(condition, message):
        if not condition:
            raise ValueError(f"Invalid adequacy artifact: {message}")

    def number(value, nullable=False, low=0, high=None):
        return (value is None and nullable) or (type(value) in (int, float) and math.isfinite(value)
                and value >= low and (high is None or value <= high))

    def integer(value):
        return type(value) is int and value >= 0

    require(isinstance(document, dict) and document.get("type") == "FeatureCollection", "not a FeatureCollection")
    meta = document.get("analysis")
    require(isinstance(meta, dict), "missing analysis metadata")
    require(meta.get("schema_version") == "1" and meta.get("method_version") == "1", "unsupported schema/method version")
    start, end = month_bounds(meta.get("month", ""))
    require(meta.get("id") == f"adequacy-{meta['month']}", "identity does not match period")
    require(meta.get("complete") is True and meta.get("period_start") == start.isoformat()
            and meta.get("period_end") == end.isoformat(), "incomplete or invalid monthly period")
    require(meta.get("fill_provenance") in ("synthetic", "observed"), "unknown fill provenance")
    require(isinstance(meta.get("source_fingerprints"), dict) and bool(meta["source_fingerprints"]), "missing source fingerprints")
    require(all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                for v in meta["source_fingerprints"].values()), "invalid source hash")
    require(isinstance(meta.get("input_fingerprint"), str) and bool(re.fullmatch(r"[a-f0-9]{64}", meta["input_fingerprint"])), "invalid input fingerprint")
    require(isinstance(meta.get("policy"), dict) and isinstance(meta.get("quality"), dict)
            and isinstance(meta.get("priors"), dict) and isinstance(meta.get("assumptions"), list), "missing method/quality metadata")
    policy = meta['policy']
    for key in ('pressure_quantile', 'min_bin_coverage', 'excess_rate', 'exceedance_probability'):
        require(number(policy.get(key), high=1), f'policy {key}')
    require(number(policy.get('access_distance_m')) and policy['access_distance_m'] > 0, 'access policy')
    require(number(policy.get('suppressed_density'), high=10), 'suppressed population policy')
    require(all(integer(policy.get(key)) and policy[key] > 0 for key in ('min_assessments', 'min_assessed_days')), 'evidence policy')
    require(set(meta['priors']) == set(WASTE_TYPES), 'missing type priors')
    for prior in meta['priors'].values():
        if prior is None:
            continue
        require(isinstance(prior, dict) and prior.get('converged') is True, 'unconverged prior')
        require(all(number(prior.get(key)) and prior[key] > 0 for key in ('alpha', 'beta', 'concentration')), 'prior parameters')
        require(number(prior.get('mean'), high=1) and integer(prior.get('points')) and prior['points'] > 0, 'prior summary')
    quality = meta['quality']
    require(isinstance(quality.get('calendar'), dict) and quality['calendar'].get('complete') is True, 'calendar coverage')
    require(isinstance(quality.get('excluded_registry_bins'), list) and all(integer(x) for x in quality['excluded_registry_bins']), 'excluded bins')
    summaries = quality.get('point_summaries', {})
    require(isinstance(summaries, dict) and set(summaries) == set(WASTE_TYPES), 'point summaries')
    for summary in summaries.values():
        require(isinstance(summary, dict) and all(integer(summary.get(k)) for k in ('points', 'assessed_points', 'assessments', 'level4_count')), 'point counts')
        require(summary['assessed_points'] <= summary['points'] and summary['level4_count'] <= summary['assessments'], 'point count bounds')
    thresholds = meta.get("pressure_thresholds", {})
    require(set(thresholds) == set(WASTE_TYPES) and all(number(x, nullable=True) for x in thresholds.values()), "pressure references")
    features = document.get("features")
    require(isinstance(features, list), "missing features")
    identities, area_types, point_evidence = set(), {}, {}
    for feature in features:
        require(isinstance(feature, dict) and feature.get("type") == "Feature", "invalid feature")
        identity = feature.get("id")
        require(integer(identity) and identity not in identities, "duplicate/invalid feature ID")
        identities.add(identity)
        geometry = feature.get("geometry", {})
        rings = geometry.get("coordinates")
        require(geometry.get("type") == "Polygon" and isinstance(rings, list) and bool(rings), "invalid polygon")
        for ring in rings:
            require(isinstance(ring, list) and len(ring) >= 4 and ring[0] == ring[-1], "unclosed/short ring")
            require(all(isinstance(v, (list, tuple)) and len(v) == 2
                        and number(v[0], low=-180, high=180) and number(v[1], low=-90, high=90) for v in ring), "invalid coordinates")
        p = feature.get("properties", {})
        require(isinstance(p, dict) and p.get("waste_type") in WASTE_TYPES, "unknown waste type")
        cell = p.get("population_cell_id")
        require(integer(cell) and identity == cell * 10 + WASTE_TYPES.index(p["waste_type"]) + 1, "unstable area/type identity")
        area_types.setdefault(cell, set()).add(p["waste_type"])
        require(p.get("category") in CATEGORIES and isinstance(p.get("reasons"), list)
                and all(r in ('unknown_population', 'no_resident_demand', 'no_serving_point', 'high_pressure',
                              'long_access', 'insufficient_fill_evidence', 'elevated_level4') for r in p['reasons']), "category/reasons")
        for key in ("residents", "attributed_capacity_m3", "point_capacity_m3", "point_residents", "pressure", "distance_m"):
            require(key in p and number(p[key], nullable=True), key)
        require(number(p.get("area_ha")) and type(p.get("population_known")) is bool
                and type(p.get("suppressed")) is bool, "population metadata")
        require(p["population_known"] == (p["residents"] is not None), "population missingness")
        require(type(p.get("high_pressure")) is bool and type(p.get("long_access")) is bool, "pressure/access flags")
        for key in ("assessments", "level4_count", "assessed_days", "assessed_bins", "point_bin_count"):
            require(integer(p.get(key)), key)
        require(p["level4_count"] <= p["assessments"] and p["assessed_days"] <= p["assessments"]
                and p["assessed_days"] <= end.day and p["assessed_bins"] <= p["point_bin_count"], "count bounds")
        for key in ("raw_frequency", "smoothed_frequency", "interval_low", "interval_high", "exceedance_probability"):
            require(key in p and number(p[key], nullable=True, high=1), key)
        require(number(p.get("bin_coverage"), high=1) and type(p.get("sufficient_evidence")) is bool, "coverage")
        require(math.isclose(p['bin_coverage'], p['assessed_bins'] / p['point_bin_count'] if p['point_bin_count'] else 0, abs_tol=1e-10), 'bin coverage/count mismatch')
        if p["assessments"]:
            require(p["raw_frequency"] is not None and math.isclose(p["raw_frequency"], p["level4_count"] / p["assessments"], abs_tol=1e-10), "raw frequency/count mismatch")
            require(all(p[k] is not None for k in ("interval_low", "interval_high", "smoothed_frequency", "exceedance_probability")), "missing assessed estimate")
            require(p["interval_low"] <= p["interval_high"], "posterior bounds")
        else:
            require(all(p[k] is None for k in ("raw_frequency", "smoothed_frequency", "interval_low", "interval_high", "exceedance_probability")), "invented unassessed frequency")
        point_id = p.get("point_id")
        require(point_id is None or integer(point_id), "point identity")
        if point_id is not None:
            key = p["waste_type"], point_id
            evidence = tuple(p[k] for k in ("assessments", "level4_count", "assessed_days", "assessed_bins", "point_bin_count", "smoothed_frequency"))
            require(key not in point_evidence or point_evidence[key] == evidence, "inconsistent shared point evidence")
            point_evidence[key] = evidence
    require(all(types == set(WASTE_TYPES) for types in area_types.values()), "missing waste types for area")
    require(bool(features), "no area features")
    require(quality.get('category_counts') == dict(Counter(f['properties']['category'] for f in features)), 'category summary mismatch')
    return document


@lru_cache(maxsize=4)
def _read_cached(path: str, modified_ns: int, size: int, inode: int) -> tuple[dict, str]:
    content = Path(path).read_bytes()
    data = validate_artifact(json.loads(content))
    return data, hashlib.sha256(content).hexdigest()


def read_artifact(path: Path, directory: Path) -> tuple[dict, str]:
    resolved = path.resolve()
    if resolved.parent != directory.resolve() or not ARTIFACT_PATTERN.fullmatch(path.name):
        raise ValueError("Analysis path is outside the published catalog")
    stat = resolved.stat()
    document, revision = _read_cached(str(resolved), stat.st_mtime_ns, stat.st_size, stat.st_ino)
    if path.name != f"adequacy_{document['analysis']['month']}.geojson":
        raise ValueError("Artifact filename and period disagree")
    return document, revision


def list_analyses(directory: Path) -> dict:
    if not directory.exists():
        return {"analyses": []}
    results = []
    for path in sorted(directory.iterdir()):
        if path.suffix != ".geojson":
            continue
        if not ARTIFACT_PATTERN.fullmatch(path.name):
            if "_through_" in path.name:
                continue  # Reserved for the deferred shared-today integration.
            raise ValueError(f"Unsupported published analysis filename: {path.name}")
        document, revision = read_artifact(path, directory)
        meta = document["analysis"]
        results.append({k: meta[k] for k in ("id", "month", "period_start", "period_end", "complete",
                                             "schema_version", "method_version", "fill_provenance")} | {"revision": revision})
    return {"analyses": sorted(results, key=lambda x: x["period_end"], reverse=True)}


def get_analysis(directory: Path, analysis_id: str) -> tuple[dict, str]:
    match = re.fullmatch(r"adequacy-(\d{4}-\d{2})", analysis_id)
    if not match:
        raise FileNotFoundError("Unknown analysis")
    return read_artifact(directory / f"adequacy_{match[1]}.geojson", directory)
