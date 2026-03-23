import os
from types import SimpleNamespace

import pytest

from app.services.provider_secret_crypto import encrypt_secret
from app.tasks import analysis as analysis_task


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _ExecResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return _ScalarResult(self._value)


class _FakeDb:
    def __init__(self, row=None):
        self._row = row

    async def execute(self, _stmt):
        return _ExecResult(self._row)


@pytest.mark.asyncio
async def test_resolve_provider_api_key_prefers_active_db_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    row = SimpleNamespace(
        encrypted_secret=encrypt_secret("db-openai-key"),
        provider="openai",
        name="primary",
        is_active=True,
        is_default=True,
    )

    result = await analysis_task._resolve_provider_api_key(_FakeDb(row), "openai")

    assert result == "db-openai-key"


@pytest.mark.asyncio
async def test_resolve_provider_api_key_falls_back_to_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    result = await analysis_task._resolve_provider_api_key(_FakeDb(None), "openai")

    assert result == "env-openai-key"


@pytest.mark.asyncio
async def test_resolve_provider_api_key_supports_anthropic_alias(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    row = SimpleNamespace(
        encrypted_secret=encrypt_secret("db-claude-key"),
        provider="anthropic",
        name="default",
        is_active=True,
        is_default=True,
    )

    result = await analysis_task._resolve_provider_api_key(_FakeDb(row), "claude")

    assert result == "db-claude-key"
