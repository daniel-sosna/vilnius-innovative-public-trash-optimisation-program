"""Repeatable storage audit in a temporary, isolated PostgreSQL database."""
import json
import os
from pathlib import Path
import tempfile
from copy import deepcopy
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.infrastructure.models import ContainerAdequacyAnalysis
from app.interfaces.container_adequacy.verify import artifact_audit
from app.interfaces.container_adequacy_import.importer import parse_analysis, import_analyses


def audit():
    original_url = Settings().database_url
    name = 'adequacy_audit_' + uuid4().hex
    admin = create_engine(original_url, isolation_level='AUTOCOMMIT', hide_parameters=True)
    engine = None
    original_env = os.environ.get('DATABASE_URL')
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE {name}'))
        os.environ['DATABASE_URL'] = make_url(original_url).set(database=name).render_as_string(hide_password=False)
        config = Config('alembic.ini')
        command.upgrade(config, '0018')
        engine = create_engine(os.environ['DATABASE_URL'], hide_parameters=True)
        table = ContainerAdequacyAnalysis.__table__
        def insert(identity, meta):
            with engine.begin() as connection:
                connection.execute(table.insert().values(id=identity, revision='a'*64,
                    type='FeatureCollection', analysis=meta, features=[]))
        insert('adequacy-2026-08', {'id': 'adequacy-2026-08', 'complete': True})
        command.upgrade(config, 'head')
        insert('adequacy-2026-09-18', {'id': 'adequacy-2026-09-18', 'complete': False})
        for index, meta in enumerate(({}, {'complete': None}, {'complete': 'false'}, {'complete': 0}, {'id': 'wrong', 'complete': False})):
            identity = f'invalid-{index}'
            if 'id' not in meta:
                meta['id'] = identity
            try:
                insert(identity, meta)
            except IntegrityError:
                pass
            else:
                raise ValueError('Invalid completion/identity accepted')
        with engine.begin() as connection:
            assert connection.execute(text('SELECT count(*) FROM container_adequacy_analyses')).scalar_one() == 2
            connection.execute(text("DELETE FROM container_adequacy_analyses WHERE id = 'adequacy-2026-09-18'"))
        with tempfile.TemporaryDirectory() as temporary:
            files = []
            for doc in artifact_audit(include_documents=True):
                path = Path(temporary) / (doc['analysis']['id'] + '.geojson')
                path.write_text(json.dumps(doc))
                files.append(path)
            records = [parse_analysis(path) for path in files]
            def rows():
                with engine.connect() as connection:
                    return list(connection.execute(text('SELECT id, revision FROM container_adequacy_analyses ORDER BY id')))
            before = rows()
            invalid = Path(temporary) / 'invalid.geojson'
            invalid.write_text('{}')
            try:
                batch = [parse_analysis(path) for path in [*files, invalid]]
                with engine.begin() as connection:
                    import_analyses(connection, batch)
            except ValueError:
                pass
            else:
                raise ValueError('Invalid batch accepted')
            assert rows() == before
            with engine.begin() as connection:
                import_analyses(connection, records)
            imported = rows()
            with engine.begin() as connection:
                import_analyses(connection, records)
            assert rows() == imported
            replacement = deepcopy(artifact_audit(include_documents=True)[1])
            replacement['analysis']['input_fingerprint'] = 'c'*64
            files[1].write_text(json.dumps(replacement))
            changed = parse_analysis(files[1])
            with engine.begin() as connection:
                import_analyses(connection, [changed])
            assert dict(rows())[changed['id']] == changed['revision']
            assert {k: v for k, v in rows() if k != changed['id']} == {k: v for k, v in imported if k != changed['id']}
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM container_adequacy_analyses WHERE id LIKE 'adequacy-2026-09-%'"))
        command.downgrade(config, '0018')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT count(*) FROM container_adequacy_analyses')).scalar_one() == 1
        print(json.dumps({'migration': 'passed', 'legacy_preserved': True, 'partial_accepted': True,
                          'invalid_rows_rejected': 5, 'rollback': 'passed', 'batch_rejection': 'atomic', 'reimport': 'idempotent', 'revision_replacement': 'passed'}))
    finally:
        if engine:
            engine.dispose()
        if original_env is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = original_env
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)'))
        admin.dispose()


if __name__ == '__main__':
    audit()
