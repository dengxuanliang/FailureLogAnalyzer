"""Factory for constructing LLM providers from config."""
from __future__ import annotations

from app.llm.providers.base import BaseLlmProvider
from app.llm.providers.claude_provider import ClaudeProvider
from app.llm.providers.openai_provider import OpenAIProvider


def create_provider(
    provider_name: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> BaseLlmProvider:
    normalized = provider_name.lower()
    if normalized in {"openai", "local"}:
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
    if normalized == "claude":
        return ClaudeProvider(api_key=api_key, model=model, base_url=base_url)
    raise ValueError(
        f"Unknown LLM provider: {provider_name!r}. Supported providers: openai, claude, local"
    )
