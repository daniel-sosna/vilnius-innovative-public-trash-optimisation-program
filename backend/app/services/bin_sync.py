"""Manual, response-atomic VASA import with persistent resume and bounded refresh."""

import hashlib
import json
import logging
import math
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass

from app.core.config import Settings
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, SYNC_STATEMENT_TIMEOUT_MS
from app.infrastructure.models import (
    Bin,
    BinHist,
    Site,
    VasaImportProgress,
    VasaImportRun,
)
from app.integrations.vasa import (
    DEFAULT_BBOX,
    VasaClient,
    VasaError,
    collection_tiles,
    eligible,
    external_id,
    map_bin,
    site_identity,
)
from sqlalchemy import and_, delete, exists, func, select, text, update
from sqlalchemy import insert as plain_insert
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)
S, B, H = Site.__table__, Bin.__table__, BinHist.__table__
R, P = VasaImportRun.__table__, VasaImportProgress.__table__
IMPORT_LOCK = 1447121730
BATCH_SIZE = 250


class BinSyncError(Exception):
    pass


@dataclass(frozen=True)
class ImportOptions:
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX
    zoom: int = 17
    workers: int = 4
    max_sites: int = 10
    max_tiles: int = 0

    @property
    def trial(self):
        return bool(self.max_sites or self.max_tiles)

    def validate(self):
        import math

        if (
            isinstance(self.zoom, bool)
            or not 0 <= self.zoom <= 22
            or self.workers <= 0
            or self.max_sites < 0
            or self.max_tiles < 0
        ):
            raise ValueError(
                "zoom must be 0–22, workers positive, and limits nonnegative"
            )
        west, south, east, north = self.bbox
        if (
            not all(math.isfinite(v) for v in self.bbox)
            or not -180 <= west < east <= 180
            or not -85.051128 <= south < north <= 85.051128
        ):
            raise ValueError(
                "bbox must be finite ordered west south east north in Web Mercator bounds"
            )


@dataclass(frozen=True)
class SyncSummary:
    run_id: int
    resumed: bool
    phase: str
    fetched: int
    bins_written: int
    history_written: int
    failures: int
    removed: int
    exit_code: int


@contextmanager
def transaction(sessions):
    with sessions.begin() as session:
        session.execute(
            text(f"SET LOCAL statement_timeout = {SYNC_STATEMENT_TIMEOUT_MS}")
        )
        session.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
        yield session


def bounded_responses(pool, work, fetch, workers):
    """At most workers futures and one consumed response, including slow writers."""
    iterator, pending = iter(work), {}
    exhausted = False
    while pending or not exhausted:
        while not exhausted and len(pending) < workers:
            try:
                item = next(iterator)
            except StopIteration:
                exhausted = True
                break
            pending[pool.submit(fetch, item)] = item
        if not pending:
            break
        done, _ = wait(pending, return_when=FIRST_COMPLETED)
        for future in done:
            item = pending.pop(future)
            try:
                result, error = future.result(), None
            except Exception as failure:
                result, error = None, failure
            yield item, result, error


class Importer:
    def __init__(self, settings, sessions, options, client):
        self.settings, self.sessions, self.options, self.client = (
            settings,
            sessions,
            options,
            client,
        )
        self.token = str(uuid.uuid4())
        self.fetched = self.bins_written = self.history_written = self.removed = 0

    def _get(self, session, kind, key):
        return (
            session.execute(
                select(P).where(
                    P.c.run_id == self.run_id,
                    P.c.kind == kind,
                    P.c.work_key == str(key),
                )
            )
            .mappings()
            .first()
        )

    def _put(self, session, kind, key, complete, details):
        def json_values(value):
            if isinstance(value, float) and not math.isfinite(value):
                return None
            if isinstance(value, dict):
                return {name: json_values(item) for name, item in value.items()}
            if isinstance(value, list):
                return [json_values(item) for item in value]
            return value

        details = json_values(details)
        statement = insert(P).values(
            run_id=self.run_id,
            kind=kind,
            work_key=str(key),
            complete=complete,
            details=details,
        )
        session.execute(
            statement.on_conflict_do_update(
                index_elements=[P.c.run_id, P.c.kind, P.c.work_key],
                set_={"complete": complete, "details": details},
            )
        )

    def _failure(self, kind, key, error):
        # Never log SQLAlchemy's rendered statement/parameters or connection URL.
        original = getattr(error, "orig", error)
        reason = str(error) if isinstance(error, VasaError) else type(original).__name__
        logger.error("run=%s %s=%s failed: %s", self.run_id, kind, key, reason)
        with transaction(self.sessions) as session:
            old = self._get(session, kind, key)
            details = dict(old["details"]) if old else {}
            details.update(error=reason, attempt_token=self.token)
            self._put(session, kind, key, False, details)
            session.execute(
                update(R)
                .where(R.c.id == self.run_id)
                .values(diagnostics=R.c.diagnostics + 1)
            )

    def _select_pass(self):
        coverage = {
            "bbox": list(self.options.bbox),
            "zoom": self.options.zoom,
            "tile": self.settings.vasa_tile_url_template,
            "detail": self.settings.vasa_bin_url_template,
            "history": self.settings.vasa_history_url_template,
            "mapping_version": 1,
            "filter_version": 1,
        }
        key = hashlib.sha256(json.dumps(coverage, sort_keys=True).encode()).hexdigest()
        with transaction(self.sessions) as session:
            old = (
                session.execute(
                    select(R)
                    .where(R.c.scope_key == key)
                    .order_by(R.c.id.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
            self.resumed = bool(old and old["phase"] != "complete")
            if self.resumed:
                self.run_id, self.phase = old["id"], old["phase"]
            else:
                self.run_id = session.execute(
                    plain_insert(R)
                    .values(scope_key=key, coverage=coverage, phase="tiles")
                    .returning(R.c.id)
                ).scalar_one()
                self.phase = "tiles"
        logger.info(
            "run=%s scope=%s bbox=%s zoom=%s %s %s",
            self.run_id,
            key[:12],
            self.options.bbox,
            self.options.zoom,
            "resuming" if self.resumed else "new pass",
            "trial" if self.options.trial else "full",
        )

    def _recalculate(self, session, site_ids):
        if not site_ids:
            return
        averages = (
            select(
                B.c.site_id,
                func.avg(B.c.latitude).label("lat"),
                func.avg(B.c.longitude).label("lon"),
            )
            .where(B.c.site_id.in_(site_ids))
            .group_by(B.c.site_id)
            .subquery()
        )
        session.execute(
            update(S)
            .where(S.c.id == averages.c.site_id)
            .values(latitude=averages.c.lat, longitude=averages.c.lon)
        )
        session.execute(
            delete(S).where(
                S.c.id.in_(site_ids),
                ~exists(select(B.c.id).where(B.c.site_id == S.c.id)),
            )
        )

    def _admit(self, session, values):
        if not eligible(values, self.options.bbox):
            session.execute(
                delete(P).where(
                    P.c.run_id == self.run_id,
                    P.c.kind == "seen",
                    P.c.work_key == str(values["external_id"]),
                )
            )
            return "excluded"
        key, _ = site_identity(values)
        if self.options.max_sites and not self._get(session, "selection", key):
            count = session.scalar(
                select(func.count())
                .select_from(P)
                .where(P.c.run_id == self.run_id, P.c.kind == "selection")
            )
            if count >= self.options.max_sites:
                return "deferred"
        self._put(session, "selection", key, True, {})
        return "admitted"

    def _save_bins(self, session, rows):
        if not rows:
            return
        # Response-local batching; external IDs have already been deduplicated.
        sites, identities = {}, []
        for values in rows:
            key, address = site_identity(values)
            sites.setdefault(
                key,
                dict(
                    site_key=key,
                    address=address,
                    latitude=values["latitude"],
                    longitude=values["longitude"],
                ),
            )
            identities.append(values["external_id"])
        affected = set(
            session.scalars(select(B.c.site_id).where(B.c.external_id.in_(identities)))
        )
        statement = insert(S).values(list(sites.values()))
        site_ids = dict(
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[S.c.site_key],
                    set_={"site_key": statement.excluded.site_key},
                ).returning(S.c.site_key, S.c.id)
            ).all()
        )
        values = [dict(row, site_id=site_ids[site_identity(row)[0]]) for row in rows]
        for offset in range(0, len(values), BATCH_SIZE):
            statement = insert(B).values(values[offset : offset + BATCH_SIZE])
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[B.c.external_id],
                    set_={
                        name: statement.excluded[name]
                        for name in values[0]
                        if name != "external_id"
                    },
                )
            )
        affected.update(site_ids.values())
        self._recalculate(session, affected)

    def _resolve(self, session, identity, candidate, properties):
        values = map_bin(properties, candidate["latitude"], candidate["longitude"])
        result = self._admit(session, values)
        candidate = {key: value for key, value in candidate.items() if key != "error"}
        self._put(
            session,
            "candidate",
            identity,
            result != "deferred",
            dict(candidate, result=result, attempt_token=self.token),
        )
        if result == "admitted":
            self._put(session, "seen", identity, True, {"tile": candidate["tile"]})
            return values
        return None

    def _persist_tile(self, tile, response):
        key = "/".join(map(str, tile))
        with transaction(self.sessions) as session:
            ids, ready = set(), {}
            errors = list(response.errors)
            for candidate in response.candidates:
                identity = external_id(candidate["properties"]["id"])
                ids.add(identity)
                old = self._get(session, "candidate", identity)
                if old and "tile" in old["details"]:
                    previous = old["details"]
                    if candidate["properties"] != previous["properties"] or (
                        candidate["latitude"],
                        candidate["longitude"],
                    ) != (previous["latitude"], previous["longitude"]):
                        logger.warning(
                            "bin=%s conflicting tile observations; smallest tile then canonical payload wins",
                            identity,
                        )
                    rank = (candidate["tile"], json.dumps(candidate, sort_keys=True))
                    old_rank = (
                        previous["tile"],
                        json.dumps({k: previous[k] for k in candidate}, sort_keys=True),
                    )
                    if old_rank <= rank:
                        continue
                cached = self._get(session, "detail", identity)
                if candidate["needs_detail"] and not (cached and cached["complete"]):
                    self._put(session, "candidate", identity, False, candidate)
                    continue
                try:
                    properties = (
                        cached["details"]["properties"]
                        if cached and cached["complete"]
                        else candidate["properties"]
                    )
                    values = self._resolve(session, identity, candidate, properties)
                    if values:
                        ready[identity] = values
                except VasaError as error:
                    self._put(
                        session,
                        "candidate",
                        identity,
                        False,
                        dict(candidate, error=str(error), attempt_token=self.token),
                    )
                    errors.append(str(error))
            self._save_bins(session, list(ready.values()))
            pending = any(
                not (self._get(session, "candidate", identity) or {}).get(
                    "complete", False
                )
                for identity in ids
            )
            self._put(
                session,
                "tile",
                key,
                not errors and not pending,
                {"candidate_ids": sorted(ids), "errors": errors},
            )
            if errors:
                session.execute(
                    update(R)
                    .where(R.c.id == self.run_id)
                    .values(diagnostics=R.c.diagnostics + len(errors))
                )
        self.bins_written += len(ready)
        if errors:
            for error in errors:
                logger.error("tile=%s: %s", key, error)

    def _pending_candidates(self):
        after = 0
        while True:
            with transaction(self.sessions) as session:
                rows = (
                    session.execute(
                        select(P)
                        .where(
                            P.c.run_id == self.run_id,
                            P.c.kind == "candidate",
                            ~P.c.complete,
                            P.c.id > after,
                            func.coalesce(P.c.details["attempt_token"].astext, "")
                            != self.token,
                        )
                        .order_by(P.c.id)
                        .limit(BATCH_SIZE)
                    )
                    .mappings()
                    .all()
                )
            if not rows:
                return
            for row in rows:
                after = row["id"]
                yield row

    def _details(self, pool):
        def fetch(row):
            details = row["details"]
            identity = int(row["work_key"])
            with transaction(self.sessions) as session:
                cached = self._get(session, "detail", identity)
            if cached and cached["complete"]:
                return cached["details"]["properties"], False
            if not details["needs_detail"]:
                return details["properties"], False
            return self.client.detail(identity), True

        for row, result, error in bounded_responses(
            pool, self._pending_candidates(), fetch, self.options.workers
        ):
            identity = int(row["work_key"])
            if error:
                self._failure("candidate", identity, error)
                continue
            properties, fetched = result
            self.fetched += int(fetched)
            try:
                with transaction(self.sessions) as session:
                    candidate = self._get(session, "candidate", identity)["details"]
                    values = self._resolve(session, identity, candidate, properties)
                    if candidate["needs_detail"]:
                        self._put(
                            session,
                            "detail",
                            identity,
                            True,
                            {"properties": properties},
                        )
                    self._save_bins(session, [values] if values else [])
                self.bins_written += int(values is not None)
            except Exception as error:
                self._failure("candidate", identity, error)

    def _selected_count(self):
        with transaction(self.sessions) as session:
            return session.scalar(
                select(func.count())
                .select_from(P)
                .where(P.c.run_id == self.run_id, P.c.kind == "selection")
            )

    def _tiles(self, pool):
        def work():
            admitted_tiles = 0
            for tile in collection_tiles(self.options.bbox, self.options.zoom):
                if self.options.max_tiles and admitted_tiles >= self.options.max_tiles:
                    break
                if (
                    self.options.max_sites
                    and self._selected_count() >= self.options.max_sites
                ):
                    break
                admitted_tiles += 1
                with transaction(self.sessions) as session:
                    progress = self._get(session, "tile", "/".join(map(str, tile)))
                if not progress or not progress["complete"]:
                    yield tile

        for tile, response, error in bounded_responses(
            pool,
            work(),
            lambda tile: self.client.tile(tile, self.options.bbox),
            self.options.workers,
        ):
            self.fetched += 1
            if error:
                self._failure("tile", "/".join(map(str, tile)), error)
            else:
                try:
                    self._persist_tile(tile, response)
                except Exception as error:
                    self._failure("tile", "/".join(map(str, tile)), error)
            self._details(pool)
        self._details(pool)
        # Resolve earlier tiles waiting for detail checkpoints, without refetching.
        after = 0
        while True:
            with transaction(self.sessions) as session:
                rows = (
                    session.execute(
                        select(P)
                        .where(
                            P.c.run_id == self.run_id,
                            P.c.kind == "tile",
                            ~P.c.complete,
                            P.c.id > after,
                        )
                        .order_by(P.c.id)
                        .limit(BATCH_SIZE)
                    )
                    .mappings()
                    .all()
                )
                if not rows:
                    break
                for row in rows:
                    after = row["id"]
                    info = row["details"]
                    if info.get("error") or info.get("errors"):
                        continue
                    ids = info.get("candidate_ids", [])
                    if all(
                        (self._get(session, "candidate", identity) or {}).get(
                            "complete", False
                        )
                        for identity in ids
                    ):
                        self._put(session, "tile", row["work_key"], True, info)
        if not self.options.trial and self._tile_coverage_complete():
            self._phase("history")

    def _tile_coverage_complete(self):
        # Tile count is scalar; do not store all keys in Python.
        expected = sum(
            1 for _ in collection_tiles(self.options.bbox, self.options.zoom)
        )
        with transaction(self.sessions) as session:
            complete = session.scalar(
                select(func.count())
                .select_from(P)
                .where(P.c.run_id == self.run_id, P.c.kind == "tile", P.c.complete)
            )
            pending = session.scalar(
                select(func.count())
                .select_from(P)
                .where(
                    P.c.run_id == self.run_id, P.c.kind == "candidate", ~P.c.complete
                )
            )
        return complete == expected and not pending

    def _phase(self, phase):
        with transaction(self.sessions) as session:
            session.execute(update(R).where(R.c.id == self.run_id).values(phase=phase))
        self.phase = phase

    def _history_targets(self):
        after = 0
        while True:
            with transaction(self.sessions) as session:
                rows = (
                    session.execute(
                        select(P)
                        .where(
                            P.c.run_id == self.run_id,
                            P.c.kind == "seen",
                            P.c.complete,
                            P.c.id > after,
                        )
                        .order_by(P.c.id)
                        .limit(BATCH_SIZE)
                    )
                    .mappings()
                    .all()
                )
                targets = []
                for row in rows:
                    after = row["id"]
                    identity = int(row["work_key"])
                    checkpoint = self._get(session, "history_bin", identity)
                    if not checkpoint or not checkpoint["complete"]:
                        targets.append(
                            (
                                identity,
                                checkpoint["details"].get("next_page", 1)
                                if checkpoint
                                else 1,
                            )
                        )
            if not rows:
                return
            yield from targets

    def _persist_history(self, identity, page, response):
        with transaction(self.sessions) as session:
            old = self._get(session, "history_bin", identity)
            previous = dict(old["details"]) if old else {}
            if previous.get("restart_token") != self.token:
                previous["restarts"] = 0
            previous["restart_token"] = self.token
            previous_pagination = previous.get("pagination", {})
            changed = any(
                key in response.pagination
                and previous_pagination[key] != response.pagination[key]
                for key in previous_pagination
            )
            if changed:
                restarts = previous.get("restarts", 0) + 1
                if restarts > 5:
                    raise VasaError(
                        f"bin={identity}: pagination kept changing; restart limit exceeded"
                    )
                logger.warning(
                    "bin=%s pagination changed; restarting retrieval at page 1",
                    identity,
                )
                session.execute(
                    delete(P).where(
                        P.c.run_id == self.run_id,
                        P.c.kind == "history_page",
                        P.c.work_key.like(f"{identity}:%"),
                    )
                )
                previous = dict(previous, restarts=restarts)
                if page != 1:
                    self._put(
                        session,
                        "history_bin",
                        identity,
                        False,
                        {
                            "next_page": 1,
                            "last_page": response.last_page,
                            "pagination": response.pagination,
                            "restarts": restarts,
                            "restart_token": self.token,
                        },
                    )
                    return 1
            if response.last_page is not None and page > response.last_page:
                raise VasaError(f"bin={identity}: page exceeds indicated last_page")
            bin_id = session.scalar(select(B.c.id).where(B.c.external_id == identity))
            if bin_id is None:
                raise VasaError(f"bin={identity}: missing persistent history parent")
            rows = [dict(event, bin_id=bin_id) for event in response.events]
            for offset in range(0, len(rows), BATCH_SIZE):
                statement = insert(H).values(rows[offset : offset + BATCH_SIZE])
                session.execute(
                    statement.on_conflict_do_update(
                        index_elements=[H.c.bin_id, H.c.date, H.c.was_serviced],
                        set_={
                            "non_serviced_reason": statement.excluded.non_serviced_reason
                        },
                    )
                )
            complete = not response.errors
            self._put(
                session,
                "history_page",
                f"{identity}:{page}",
                complete,
                {
                    "last_page": response.last_page,
                    "next_page": response.next_page,
                    "errors": response.errors,
                },
            )
            self._put(
                session,
                "history_bin",
                identity,
                complete and response.next_page is None,
                {
                    "last_page": response.last_page,
                    "pagination": response.pagination,
                    "restarts": previous.get("restarts", 0),
                    "restart_token": self.token,
                    "next_page": response.next_page if complete else page,
                },
            )
            if response.errors:
                session.execute(
                    update(R)
                    .where(R.c.id == self.run_id)
                    .values(diagnostics=R.c.diagnostics + len(response.errors))
                )
        self.history_written += len(rows)
        if response.errors:
            for error in response.errors:
                logger.error("bin=%s page=%s: %s", identity, page, error)
            return None
        return response.next_page

    def _histories(self, pool):
        targets = iter(self._history_targets())
        pending, exhausted = {}, False
        while pending or not exhausted:
            while len(pending) < self.options.workers and not exhausted:
                try:
                    identity, page = next(targets)
                    pending[pool.submit(self.client.history, identity, page)] = (
                        identity,
                        page,
                    )
                except StopIteration:
                    exhausted = True
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                identity, page = pending.pop(future)
                self.fetched += 1
                try:
                    response = future.result()
                    next_page = self._persist_history(identity, page, response)
                    if next_page:
                        pending[
                            pool.submit(self.client.history, identity, next_page)
                        ] = identity, next_page
                except Exception as error:
                    # Separate failure reporting does not create a successful page checkpoint.
                    self._failure("history_bin", identity, error)
        if (
            not self.options.trial
            and self.phase == "history"
            and self._histories_complete()
        ):
            self._phase("finalize")

    def _histories_complete(self):
        history = P.alias("history_completion")
        with transaction(self.sessions) as session:
            pending = session.scalar(
                select(func.count())
                .select_from(P)
                .where(
                    P.c.run_id == self.run_id,
                    P.c.kind == "seen",
                    P.c.complete,
                    ~exists(
                        select(history.c.id).where(
                            history.c.run_id == P.c.run_id,
                            history.c.kind == "history_bin",
                            history.c.work_key == P.c.work_key,
                            history.c.complete,
                        )
                    ),
                )
            )
        return pending == 0

    def _unresolved_errors(self):
        with transaction(self.sessions) as session:
            return session.scalar(
                select(func.count())
                .select_from(P)
                .where(
                    P.c.run_id == self.run_id,
                    ~P.c.complete,
                    (P.c.details.has_key("error"))
                    | (
                        func.jsonb_array_length(
                            func.coalesce(P.c.details["errors"], text("'[]'::jsonb"))
                        )
                        > 0
                    ),
                )
            )

    def _finalize(self):
        if (
            self.options.trial
            or not self._tile_coverage_complete()
            or not self._histories_complete()
        ):
            return
        west, south, east, north = self.options.bbox
        with transaction(self.sessions) as session:
            # A temporary table keeps the affected site set inside PostgreSQL,
            # rather than collecting a city's deleted-bin IDs in Python.
            session.execute(
                text(
                    "CREATE TEMP TABLE vasa_affected_sites (id BIGINT PRIMARY KEY) ON COMMIT DROP"
                )
            )
            unseen = ~exists(
                select(P.c.id).where(
                    P.c.run_id == self.run_id,
                    P.c.kind == "seen",
                    P.c.complete,
                    P.c.work_key == func.cast(B.c.external_id, P.c.work_key.type),
                )
            )
            stale = and_(
                B.c.external_id.is_not(None),
                B.c.longitude.between(west, east),
                B.c.latitude.between(south, north),
                unseen,
            )
            session.execute(
                text(
                    "INSERT INTO vasa_affected_sites SELECT DISTINCT site_id FROM bins WHERE external_id IS NOT NULL AND longitude BETWEEN :west AND :east AND latitude BETWEEN :south AND :north AND NOT EXISTS (SELECT 1 FROM vasa_import_progress p WHERE p.run_id=:run_id AND p.kind='seen' AND p.complete AND p.work_key=bins.external_id::text)"
                ),
                dict(
                    west=west, east=east, south=south, north=north, run_id=self.run_id
                ),
            )
            removed = session.execute(delete(B).where(stale)).rowcount
            session.execute(
                text(
                    "DELETE FROM sites WHERE id IN (SELECT id FROM vasa_affected_sites) AND NOT EXISTS (SELECT 1 FROM bins WHERE site_id=sites.id)"
                )
            )
            session.execute(
                text(
                    "UPDATE sites SET latitude=a.lat, longitude=a.lon FROM (SELECT site_id,AVG(latitude) lat,AVG(longitude) lon FROM bins WHERE site_id IN (SELECT id FROM vasa_affected_sites) GROUP BY site_id) a WHERE sites.id=a.site_id"
                )
            )
            session.execute(
                update(R).where(R.c.id == self.run_id).values(phase="complete")
            )
        self.removed, self.phase = removed, "complete"

    def run(self):
        self.options.validate()
        engine = self.sessions.kw["bind"]
        with engine.connect() as lock:
            acquired = lock.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": IMPORT_LOCK}
            )
            lock.commit()
            if not acquired:
                raise BinSyncError("Another VASA importer is already running")
            try:
                self._select_pass()
                with ThreadPoolExecutor(max_workers=self.options.workers) as pool:
                    if self.phase == "tiles":
                        self._tiles(pool)
                    # Trials can still persist histories for their selected bins.
                    if self.phase in ("tiles", "history"):
                        self._histories(pool)
                if self.phase == "finalize":
                    self._finalize()
            finally:
                lock.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": IMPORT_LOCK}
                )
                lock.commit()
        unresolved = self._unresolved_errors()
        # Historical diagnostic totals do not make successfully repaired work fail.
        code = (
            0
            if self.phase == "complete"
            else 1
            if unresolved
            else 2
            if self.options.trial
            else 1
        )
        summary = SyncSummary(
            self.run_id,
            self.resumed,
            self.phase,
            self.fetched,
            self.bins_written,
            self.history_written,
            unresolved,
            self.removed,
            code,
        )
        logger.info("Import summary: %s", summary)
        if self.options.trial:
            logger.warning(
                "Incomplete trial: selected addresses may have unseen member bins; no missing-bin cleanup"
            )
        return summary


def synchronize_bins(
    settings: Settings,
    sessions: sessionmaker[Session],
    options: ImportOptions | None = None,
    *,
    client=None,
) -> SyncSummary:
    return Importer(
        settings, sessions, options or ImportOptions(), client or VasaClient(settings)
    ).run()
