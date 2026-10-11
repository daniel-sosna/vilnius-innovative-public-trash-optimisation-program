"""Repeatable diagnostic; local mode never constructs or calls a provider."""
import argparse
import asyncio
import json
import logging
import sys

from app.core.config import Settings
from app.infrastructure.database import create_analytics_engine, create_session_factory
from app.services.analytics_agent.contracts import Bbox, RunContext
from app.services.analytics_agent.guide import guide
from app.services.analytics_agent.registry import REGISTRY, catalogue, dispatch, serialize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue', action='store_true')
    parser.add_argument('--guide', action='store_true')
    parser.add_argument('--live', action='store_true', help='Explicitly call configured OpenAI model.')
    parser.add_argument('--bbox', nargs=4, type=float, metavar=('MIN_LAT', 'MIN_LON', 'MAX_LAT', 'MAX_LON'))
    parser.add_argument('--tool', choices=sorted(REGISTRY), default='get_area_overview')
    parser.add_argument('--arguments', default='{}', help='JSON tool arguments; NULL fields apply defaults.')
    parser.add_argument('--full', action='store_true', help='Print bounded JSON instead of compact evidence.')
    args = parser.parse_args()
    if args.catalogue:
        print(json.dumps(catalogue(), ensure_ascii=False, indent=2))
        return 0
    if args.guide:
        print(guide())
        return 0
    if args.bbox is None: parser.error('--bbox is required for local or live queries')
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    engine = None
    try:
        bbox = Bbox(**dict(zip(('min_latitude', 'min_longitude', 'max_latitude', 'max_longitude'), args.bbox)))
        settings = Settings()
        engine = create_analytics_engine(settings)
        factory = create_session_factory(engine)
        if args.live:
            from app.integrations.openai import ResponsesProvider
            from app.services.analytics_agent.run import analyze
            key = settings.openai_api_key.get_secret_value().strip() if settings.openai_api_key else ''
            model = (settings.openai_model or '').strip()
            if not key or not model:
                print('Live mode requires backend OPENAI_API_KEY and OPENAI_MODEL.', file=sys.stderr)
                return 2
            response = asyncio.run(analyze(factory, bbox, ResponsesProvider(key, model)))
            print(response.model_dump_json(indent=2))
            return 0 if response.status == 'complete' else 3
        ctx = RunContext(bbox)
        result = dispatch(factory, ctx, args.tool, args.arguments)
        encoded = serialize(result, ctx)
        body = json.loads(encoded)
        if args.full: print(encoded)
        else:
            print(json.dumps({'tool': args.tool, 'status': body['status'], 'code': body.get('code'), 'read_only': body['read_only'], 'bytes': len(encoded.encode()), 'data': {key: value[:3] if isinstance(value, list) else value for key, value in body['data'].items()}, 'preview_only': True}, ensure_ascii=False, indent=2))
        return 0 if body['status'] == 'ok' else 1
    except Exception as error:
        print('Diagnostic failed (' + type(error).__name__ + '); check configuration and stored data.', file=sys.stderr)
        return 1
    finally:
        if engine is not None: engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
