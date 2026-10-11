"""Operator-invoked risk contract diagnostic, with disposable database fixtures."""
from collections import Counter
from copy import deepcopy
from datetime import date
import json
import os
from time import monotonic
from time import perf_counter
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.infrastructure.database import create_analytics_engine, create_session_factory
from app.infrastructure.models import ContainerAdequacyAnalysis
from app.interfaces.container_adequacy.verify import artifact_audit
from app.interfaces.container_adequacy_import.importer import import_analyses
from app.services.adequacy_artifacts import fingerprint, validate_artifact
from app.services.analytics_agent.contracts import Bbox, RunContext
from app.services.analytics_agent.registry import definitions, dispatch, serialize


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fixture():
    doc = deepcopy(artifact_audit(include_documents=True)[1])
    templates = doc['features']
    features = []
    for cell in range(1, 24):
        for original in templates:
            feature = deepcopy(original)
            waste = feature['properties']['waste_type']
            code = feature['id'] % 10
            feature['id'] = cell * 10 + code
            properties = feature['properties']
            properties.update(population_cell_id=cell, point_id=code, residents=100,
                point_residents=300, attributed_capacity_m3=1, pressure=100, high_pressure=True,
                assessments=20, level4_count=5, assessed_days=3, assessed_bins=1,
                bin_coverage=1, raw_frequency=.25, smoothed_frequency=6/22,
                interval_low=.1, interval_high=.5, exceedance_probability=.2,
                sufficient_evidence=True, category='potential_shortage', reasons=['high_pressure'])
            if cell > 3:
                x = 25.01 + cell * .001
                feature['geometry']['coordinates'] = [[[x,54.7],[x+.001,54.7],[x+.001,54.701],[x,54.701],[x,54.7]]]
            elif cell == 1:
                feature['geometry']['coordinates'].append([[25.0003,54.7003],[25.0003,54.7007],
                    [25.0007,54.7007],[25.0007,54.7003],[25.0003,54.7003]])
            elif cell == 3:
                feature['geometry']['coordinates'] = [[[25.0006,54.7004],[25.001,54.7004],
                    [25.001,54.7006],[25.0006,54.7006],[25.0006,54.7004]]]
            if cell == 23:
                properties.update(residents=None, population_known=False, point_id=None,
                    point_capacity_m3=None, point_residents=None, attributed_capacity_m3=None,
                    pressure=None, distance_m=None, high_pressure=False, long_access=False,
                    assessments=0, level4_count=0, assessed_days=0, assessed_bins=0, point_bin_count=0,
                    bin_coverage=0, raw_frequency=None, smoothed_frequency=None, interval_low=None,
                    interval_high=None, exceedance_probability=None, sufficient_evidence=False,
                    category='unavailable', reasons=['unknown_population'])
            features.append(feature)
    for original in templates:
        feature = deepcopy(original)
        code = feature['id'] % 10
        feature['id'] = 1000 + code
        feature['properties']['population_cell_id'] = 100
        feature['geometry']['coordinates'] = [[[25,54.7],[25.001,54.701],[25,54.701],[25.001,54.7],[25,54.7]]]
        features.append(feature)
    doc['features'] = features
    meta = doc['analysis']
    meta['quality']['category_counts'] = dict(Counter(feature['properties']['category'] for feature in features))
    for waste in meta['priors']:
        meta['priors'][waste] = {'alpha': 1, 'beta': 1, 'mean': .5, 'concentration': 2, 'points': 1, 'converged': True}
        meta['pressure_thresholds'][waste] = 100
        meta['quality']['point_summaries'][waste] = {'points': 1, 'assessed_points': 1, 'assessments': 20, 'level4_count': 5}
    # The invalid geometry retains consistent shared point evidence, but is excluded by read tools.
    for feature in features:
        if feature['properties']['population_cell_id'] == 100:
            source = next(feature2 for feature2 in features if feature2['properties']['population_cell_id'] == 2
                          and feature2['properties']['waste_type'] == feature['properties']['waste_type'])
            feature['properties'] = {**source['properties'], 'population_cell_id': 100}
    meta['quality']['category_counts'] = dict(Counter(feature['properties']['category'] for feature in features))
    validate_artifact(doc)
    return doc


def audit():
    settings = Settings()
    original_url = settings.database_url
    original_env = os.environ.get('DATABASE_URL')
    name = 'risk_audit_' + uuid4().hex
    admin = create_engine(original_url, isolation_level='AUTOCOMMIT', hide_parameters=True)
    writer = reader = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE {name}'))
        url = make_url(original_url).set(database=name).render_as_string(hide_password=False)
        os.environ['DATABASE_URL'] = url
        command.upgrade(Config('alembic.ini'), 'head')
        writer = create_engine(url, hide_parameters=True)
        reader = create_analytics_engine(settings.model_copy(update={'database_url': url}))
        factory = create_session_factory(reader)
        doc = fixture()
        record = {'id': doc['analysis']['id'], 'revision': fingerprint(doc), 'type': doc['type'],
                  'analysis': doc['analysis'], 'features': doc['features']}
        with writer.begin() as connection:
            import_analyses(connection, [record])
        wide = Bbox(min_latitude=54.699, min_longitude=24.999, max_latitude=54.702, max_longitude=25.0011)
        hole = Bbox(min_latitude=54.7004, min_longitude=25.0004, max_latitude=54.7006, max_longitude=25.0006)
        outside = Bbox(min_latitude=0., min_longitude=0., max_latitude=1., max_longitude=1.)
        def context(bbox=wide, day=18):
            ctx = RunContext(bbox, date(2026, 9, day))
            overview = dispatch(factory, ctx, 'get_area_overview', '{}')
            require(overview.status == 'ok', 'Overview query failed')
            return ctx, overview.data['coverage']['container_adequacy_analyses']
        started = perf_counter()
        ctx, overview = context()
        require(overview['available'] and overview['matched_features'] == 9, 'Expected three polygons per waste stream')
        result = dispatch(factory, ctx, 'get_adequacy_summary', '{"waste_type":null}')
        require(result.status == 'ok' and result.read_only, 'Summary must execute read-only')
        for stream in result.data['streams']:
            require(stream['areas'] == 3 and stream['unique_serving_points'] == 1, 'Area/point scope differs')
            evidence = stream['serving_point_evidence']
            require(evidence['level4_count'] == 5 and evidence['assessments'] == 20, 'Shared assessment multiplication')
            require(evidence['full_point_capacity_m3'] == 3, 'Shared point capacity multiplication')
            require(stream['full_polygon_residents'] == 300, 'Full polygon population')
        require(result.data['geometry_coverage']['invalid_geometry_features'] == 3, 'Invalid geometry feedback')
        require('geometry' not in json.dumps(dispatch(factory, ctx, 'list_adequacy_features', '{}').data['records']), 'Raw geometry leaked')
        invalid = dispatch(factory, ctx, 'list_adequacy_features', '{"limit":101}')
        require(invalid.code == 'invalid_arguments', 'Maximum pagination bound')
        invalid = dispatch(factory, ctx, 'get_adequacy_summary', '{"waste_type":"unsupported"}')
        require(invalid.code == 'invalid_arguments', 'Typed waste filter')
        hole_ctx, discovered = context(hole)
        listing = dispatch(factory, hole_ctx, 'list_adequacy_features', '{}')
        ids = [entry['feature_id'] for entry in listing.data['records']]
        require(ids == [21,22,23,31,32,33], 'Hole/boundary intersection differs')
        require(dispatch(factory, hole_ctx, 'get_adequacy_feature', '{"feature_id":11}').code == 'invalid_feature', 'Out-of-area detail accepted')
        detail = dispatch(factory, hole_ctx, 'get_adequacy_feature', '{"feature_id":21}')
        require(detail.status == 'ok' and detail.data['feature']['point_id'] == 1, 'External serving point discarded')
        # No bin registry rows exist: serving-point context is saved evidence, not a bbox bin lookup.
        all_bbox = Bbox(min_latitude=54.699, min_longitude=24.999, max_latitude=54.702, max_longitude=25.1)
        page_ctx, _ = context(all_bbox)
        first = dispatch(factory, page_ctx, 'list_adequacy_features', '{}')
        second = dispatch(factory, page_ctx, 'list_adequacy_features', '{"offset":50}')
        require(first.data['returned_count'] == 50 and first.data['next_offset'] == 50, 'Default pagination')
        require(first.data['records'][-1]['feature_id'] < second.data['records'][0]['feature_id'], 'Deterministic pages')
        unknown = dispatch(factory, page_ctx, 'get_adequacy_feature', '{"feature_id":231}')
        require(unknown.status == 'ok' and unknown.data['feature']['residents'] is None
                and unknown.data['feature']['raw_frequency'] is None, 'Unknown metrics must stay null')
        empty_ctx, empty = context(outside)
        require(empty['available'] and empty['matched_features'] == 0, 'Zero matches mistaken for absence')
        missing_ctx, missing = context(day=1)
        require(missing['available'] is False and missing['code'] == 'missing_cutoff', 'Missing cutoff feedback')
        new_doc = artifact_audit(include_documents=True)[0]
        new = {'id': new_doc['analysis']['id'], 'revision': fingerprint(new_doc),
               'type': new_doc['type'], 'analysis': new_doc['analysis'], 'features': new_doc['features']}
        with writer.begin() as connection:
            import_analyses(connection, [new])
        require(dispatch(factory, missing_ctx, 'get_adequacy_summary', '{}').data['available'] is False, 'Pinned absence changed')
        with writer.begin() as connection:
            connection.execute(ContainerAdequacyAnalysis.__table__.update().where(ContainerAdequacyAnalysis.id == record['id']).values(revision='b'*64))
        require(dispatch(factory, ctx, 'get_adequacy_summary', '{}').code == 'stale_evidence', 'Replaced revision mixed into run')
        def failed_factory():
            raise SQLAlchemyError('Deliberate unavailable query fixture')
        failed = dispatch(failed_factory, RunContext(wide, date(2026,9,18)), 'get_area_overview', '{}')
        require(failed.code == 'query_failed', 'Failed read mistaken for absence/zero')
        budget_ctx = RunContext(wide, date(2026,9,18)); budget_ctx.tool_calls = 12
        require(dispatch(factory, budget_ctx, 'get_area_overview', '{}').code == 'tool_budget', 'Execution budget changed')
        expired = RunContext(wide, date(2026,9,18)); expired.started = monotonic() - 46
        require(dispatch(factory, expired, 'get_area_overview', '{}').code == 'deadline', 'Exploration deadline changed')
        require(ctx.period().date_end_exclusive != '2026-09-19', 'Observation periods were moved to the risk date')
        budget_ctx.result_bytes = 49152
        require(len(serialize(result, budget_ctx).encode()) <= 1024, 'Payload budget changed')
        for definition in definitions():
            schema = definition['parameters']
            require(definition['strict'] and schema['additionalProperties'] is False, 'Strict function schema')
            require(set(schema.get('required', [])) == set(schema.get('properties', {})), 'Nullable strict fields must be required')
        print(json.dumps({'risk_contracts': 'passed', 'provider_calls': 0, 'read_only': True,
                          'spatial_contracts': 'holes, boundaries, invalid geometry and external points',
                          'deduplicated_counts': '5/20', 'pagination': 'default 50/max 100',
                          'missing_zero_failed': 'distinct', 'revision_and_absence_pinning': 'passed',
                          'seconds': round(perf_counter() - started, 3)}))
        return 0
    except Exception as error:
        print(json.dumps({'risk_contracts': 'failed', 'error_type': type(error).__name__,
                          'message': str(error) if isinstance(error, ValueError) else 'Check diagnostic configuration and stored data.'}))
        return 1
    finally:
        if reader is not None:
            reader.dispose()
        if writer is not None:
            writer.dispose()
        if original_env is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = original_env
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)'))
        admin.dispose()
