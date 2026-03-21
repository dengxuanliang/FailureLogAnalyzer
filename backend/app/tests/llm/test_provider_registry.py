import pytest

from app.llm.providers.claude_provider import ClaudeProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.registry import create_provider


def test_create_provider_openai_and_local_alias():
    openai_provider = create_provider("openai", api_key="k", model="gpt-4o")
    local_provider = create_provider("local", api_key="k", model="gpt-4o", base_url="http://localhost:8000/v1")

    assert isinstance(openai_provider, OpenAIProvider)
    assert isinstance(local_provider, OpenAIProvider)


def test_create_provider_claude():
    provider = create_provider("claude", api_key="k", model="claude-sonnet-4")
    assert isinstance(provider, ClaudeProvider)


def test_create_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_provider("bogus", api_key="k", model="x")
