"""One bounded run: overview, investigation, synthesis, no persisted conversation."""
import asyncio
import json
import logging
from time import monotonic

from .contracts import AnalysisResponse, RunContext
from .guide import guide
from .registry import definitions, dispatch, serialize

logger = logging.getLogger(__name__)


def execute_batch(factory, ctx, calls, first=False, progress=None):
    outputs = []
    for index, call in enumerate(calls):
        if index >= 4 or ctx.tool_calls >= 12:
            output = json.dumps({'status': 'error', 'code': 'tool_budget', 'message': 'At most four executed calls per response and twelve per run.'})
        elif ctx.remaining(True) <= 0:
            output = json.dumps({'status': 'error', 'code': 'deadline', 'message': 'Investigation budget exhausted; synthesize available evidence.'})
        elif first and call.name != 'get_area_overview':
            output = json.dumps({'status': 'error', 'code': 'overview_required'})
        elif ctx.result_bytes >= 49152:
            output = json.dumps({'status': 'error', 'code': 'result_budget'})
        else:
            if progress:
                progress({"stage": "tool", "tool": call.name})
            result = dispatch(factory, ctx, call.name, call.arguments)
            output = serialize(result, ctx)
            outputs.append({'type': 'function_call_output', 'call_id': call.call_id, 'output': output})
            continue
        ctx.result_bytes += len(output.encode())
        outputs.append({'type': 'function_call_output', 'call_id': call.call_id, 'output': output})
    return outputs


async def analyze(factory, bbox, provider, context=None, progress=None):
    ctx = context or RunContext(bbox)
    instructions = guide()
    history = [{'role': 'user', 'content': json.dumps({'bbox': bbox.model_dump(), 'default_period': ctx.period().model_dump(), 'request': 'Analyze this area from tool evidence. Answer in Lithuanian.'})}]
    tools = definitions()
    requests = 0
    answer = None
    reason = 'no_final_answer'
    complete = False
    logger.info('analytics start run=%s', ctx.correlation_id)
    try:
        while requests < 5 and ctx.remaining() > 0:
            synthesis = requests == 4 or ctx.remaining(True) <= 0 or ctx.tool_calls >= 12 or ctx.result_bytes >= 49152
            if synthesis:
                history.append({'role': 'user', 'content': 'Synthesize only returned evidence now; no further tools. Explain failed reads, missing data and limitations.'})
            timeout = ctx.remaining() if synthesis else min(12.0, ctx.remaining(True))
            if timeout <= 0: continue
            if progress:
                progress({"stage": "synthesis" if synthesis else "investigation", "round": requests + 1})
            requests += 1  # Count before dispatch, including failed outbound requests.
            try:
                async with asyncio.timeout(timeout):
                    response = await provider.request(instructions=instructions, history=history, tools=tools, first=requests == 1, synthesis=synthesis, timeout=timeout)
            except TimeoutError:
                if synthesis or ctx.remaining() <= 0:
                    reason = 'deadline'
                    break
                # A bounded investigation wait leaves the synthesis reserve available.
                history.append({'role': 'user', 'content': 'The investigation request timed out. Use existing evidence and disclose incomplete coverage.'})
                if requests == 1:
                    reason = 'deadline'
                    break
                continue
            history.extend(item.model_dump(mode='json', exclude_none=True) for item in response.output)
            calls = [item for item in response.output if item.type == 'function_call']
            refused = any(item.type == 'message' and any(part.type == 'refusal' for part in item.content) for item in response.output)
            answer = response.output_text.strip() or None
            if refused:
                reason = 'refused'
                break
            if calls:
                if synthesis:
                    reason = 'no_final_answer'
                    break
                history.extend(await asyncio.to_thread(execute_batch, factory, ctx, calls, requests == 1, progress))
                if requests == 1 and not any(call.name == 'get_area_overview' for call in calls):
                    reason = 'no_final_answer'
                    answer = None
                    break
                answer = None
                continue
            if response.status != 'completed':
                reason = 'model_response_incomplete'
                break
            if answer and requests > 1:
                complete = True
                reason = None
                break
            if requests == 1:
                answer = None
                reason = 'no_final_answer'
                break
        if not complete and ctx.remaining() <= 0: reason = 'deadline'
        return AnalysisResponse(status='complete' if complete else 'incomplete', bbox=bbox, default_period=ctx.period(), answer=answer, incomplete_reason=reason, model_requests=requests, elapsed_seconds=round(monotonic() - ctx.started, 3))
    except Exception as error:
        logger.warning('analytics failed run=%s type=%s requests=%s duration=%.3f', ctx.correlation_id, type(error).__name__, requests, monotonic() - ctx.started)
        raise
    finally:
        await provider.close()
        logger.info('analytics finish run=%s status=%s reason=%s requests=%s tools=%s bytes=%s duration=%.3f', ctx.correlation_id, 'complete' if complete else 'incomplete', reason, requests, ctx.tool_calls, ctx.result_bytes, monotonic() - ctx.started)
