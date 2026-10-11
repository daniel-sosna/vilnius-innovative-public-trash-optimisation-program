"""Backend-only Responses adapter; request retries are disabled."""
from openai import AsyncOpenAI, APIError


class ProviderFailure(Exception):
    """Safe provider failure without exception payloads or credentials."""


class ResponsesProvider:
    def __init__(self, key, model):
        self.model = model
        self.client = AsyncOpenAI(api_key=key, max_retries=0)

    async def request(self, *, instructions, history, tools, first, synthesis, timeout):
        choice = 'none' if synthesis else {'type': 'function', 'name': 'get_area_overview'} if first else 'auto'
        try:
            return await self.client.responses.create(
                model=self.model, instructions=instructions, input=history,
                tools=[] if synthesis else tools, tool_choice=choice,
                store=False, include=['reasoning.encrypted_content'],
                max_output_tokens=4000, timeout=timeout,
            )
        except APIError:
            raise ProviderFailure('Provider request failed') from None

    async def close(self):
        await self.client.close()
