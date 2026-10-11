"""Run from backend: python ../openspec/changes/archive/2026-10-11-monthly-container-adequacy/verify_api.py

Uses DATABASE_URL; creates/drops only a unique schema, preserving public tables and files.
Requires generated August and September artifacts.
"""
import json
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path.cwd()))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, data_dir
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.models import ContainerAdequacyAnalysis
from app.interfaces.container_adequacy_import.importer import import_analyses, parse_analysis
from app.interfaces.map_analytics.router import router
from app.services.adequacy_artifacts import output_directory


def main():
    started = perf_counter()
    record = parse_analysis(output_directory(data_dir()) / 'adequacy_2026-09.geojson')
    engine = create_database_engine(Settings())
    schema = 'adequacy_verify_' + uuid4().hex
    isolated = engine.execution_options(schema_translate_map={None: schema})
    results = {}
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with isolated.begin() as connection:
            ContainerAdequacyAnalysis.__table__.create(connection)
        app = FastAPI()
        app.state.sessions = create_session_factory(isolated)
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        def request(suffix, expected):
            response = client.get('/map-analytics/adequacy-analyses' + suffix)
            if response.status_code != expected:
                raise ValueError(f'{suffix}: got {response.status_code}, expected {expected}')
            return response

        assert request('', 200).json() == {'analyses': []}
        request('/unknown', 404)
        request('/adequacy-2025-01', 404)
        request('/..%5Coutside', 404)
        with isolated.begin() as connection:
            import_analyses(connection, [record])
        first = request('', 200).json()['analyses'][0]
        response = request('/' + record['id'], 200)
        document = response.json()
        assert document == {k: record[k] for k in ('type', 'analysis', 'features')}
        assert response.headers['etag'] == '"' + record['revision'] + '"'
        results['round_trip_features'] = len(document['features'])
        results['round_trip_bytes'] = len(response.content)
        results['revision_before'] = first['revision']
        del document, response

        def row_versions():
            with engine.connect() as connection:
                return list(connection.execute(text(
                    f'SELECT id, revision, xmin::text FROM "{schema}".container_adequacy_analyses ORDER BY id'
                )))

        before = row_versions()
        with isolated.begin() as connection:
            import_analyses(connection, [record])
        assert row_versions() == before, 'Same revision must be a no-op'
        changed = {**record, 'revision': 'a' * 64}
        invalid = {**record, 'id': 'adequacy-2026-08', 'revision': 'invalid'}
        try:
            with isolated.begin() as connection:
                import_analyses(connection, [changed, invalid])
        except IntegrityError:
            pass
        else:
            raise ValueError('Invalid revision unexpectedly accepted')
        assert row_versions() == before, 'Failed batch changed stored rows'

        with tempfile.TemporaryDirectory(dir=data_dir()) as directory:
            invalid_path = Path(directory) / 'invalid.geojson'
            invalid_path.write_text('{}')
            try:
                parse_analysis(invalid_path)
            except ValueError:
                pass
            else:
                raise ValueError('Malformed input accepted')
        assert row_versions() == before

        unrelated = parse_analysis(output_directory(data_dir()) / 'adequacy_2026-08.geojson')
        with isolated.begin() as connection:
            import_analyses(connection, [unrelated])
        unrelated_before = row_versions()[0]
        with isolated.begin() as connection:
            import_analyses(connection, [changed])
        assert row_versions()[0] == unrelated_before, 'Unrelated month changed'
        entries = request('', 200).json()['analyses']
        assert [x['month'] for x in entries] == ['2026-09', '2026-08']
        assert entries[0]['revision'] == changed['revision']
        results['revision_after'] = entries[0]['revision']
        assert request('/' + record['id'], 200).headers['etag'] == '"' + changed['revision'] + '"'
        with isolated.begin() as connection:
            ContainerAdequacyAnalysis.__table__.drop(connection)
        request('', 500)
        request('/' + record['id'], 500)
        results['checks'] = 'passed: PostgreSQL JSONB round trip, empty, unknown, traversal, idempotency, atomic rollback, invalid input, unrelated months, latest ordering, revision/ETag, database errors'
        results['seconds'] = round(perf_counter() - started, 2)
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
    target = Path(__file__).with_name('api-verification.json')
    target.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
