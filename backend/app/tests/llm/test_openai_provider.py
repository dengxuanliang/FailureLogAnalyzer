import pytest

from app.llm.providers.base import BaseLlmProvider, LlmResponse
from app.llm.providers.openai_provider import OpenAIProvider


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    async def post(self, url: str, json: dict, headers: dict, timeout: float):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return _FakeResponse(self.payload)


class _FailingHttpClient:
    async def post(self, url: str, json: dict, headers: dict, timeout: float):
        raise RuntimeError("rate limited")


class DummyProvider(BaseLlmProvider):
    async def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.0, max_tokens: int = 2048):
        return LlmResponse(text="{}", prompt_tokens=1, completion_tokens=1, model="dummy")


def test_base_provider_contract_can_be_implemented():
    provider = DummyProvider()
    assert isinstance(provider, BaseLlmProvider)


def test_llm_response_total_tokens_property():
    response = LlmResponse(text="{}", prompt_tokens=12, completion_tokens=5, model="m")
    assert response.total_tokens == 17


@pytest.mark.asyncio
async def test_openai_provider_call_success():
    fake_payload = {
        "model": "gpt-4o",
        "choices": [{"message": {"content": "{\"ok\":true}"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 7},
    }
    fake_client = _FakeHttpClient(fake_payload)
    provider = OpenAIProvider(api_key="k", model="gpt-4o", base_url="https://example.com", client=fake_client)

    response = await provider.call(system_prompt="sys", user_prompt="usr", temperature=0.2, max_tokens=42)

    assert response.text == '{"ok":true}'
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 7
    assert response.model == "gpt-4o"
    assert fake_client.calls[0]["url"] == "https://example.com/chat/completions"
    assert fake_client.calls[0]["json"]["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_openai_provider_raises_upstream_error():
    provider = OpenAIProvider(api_key="k", model="gpt-4o", client=_FailingHttpClient())

    with pytest.raises(RuntimeError, match="rate limited"):
        await provider.call(system_prompt="sys", user_prompt="usr")
