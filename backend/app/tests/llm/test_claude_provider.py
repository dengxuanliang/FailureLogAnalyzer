import pytest

from app.llm.providers.claude_provider import ClaudeProvider


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


@pytest.mark.asyncio
async def test_claude_provider_call_success():
    fake_payload = {
        "model": "claude-sonnet-4",
        "content": [{"type": "text", "text": "{\"ok\": true}"}],
        "usage": {"input_tokens": 22, "output_tokens": 11},
    }
    fake_client = _FakeHttpClient(fake_payload)
    provider = ClaudeProvider(api_key="k", model="claude-sonnet-4", base_url="https://anthropic.example", client=fake_client)

    response = await provider.call(system_prompt="sys", user_prompt="usr")

    assert response.text == '{"ok": true}'
    assert response.prompt_tokens == 22
    assert response.completion_tokens == 11
    assert response.model == "claude-sonnet-4"
    assert fake_client.calls[0]["url"] == "https://anthropic.example/messages"
    assert fake_client.calls[0]["headers"]["anthropic-version"] == "2023-06-01"
