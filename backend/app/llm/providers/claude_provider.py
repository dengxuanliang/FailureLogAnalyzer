"""Anthropic Claude provider implementation via HTTP API."""
from __future__ import annotations

from typing import Any

import httpx

from app.llm.providers.base import BaseLlmProvider, LlmResponse


class ClaudeProvider(BaseLlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
        timeout: float = 30.0,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self._timeout = timeout
        self._client = client or httpx.AsyncClient()

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        response = await self._client.post(
            f"{self._base_url}/messages",
            json={
                "model": self._model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()

        content = payload.get("content") or []
        text = ""
        if content:
            text = content[0].get("text") or ""

        usage = payload.get("usage") or {}
        return LlmResponse(
            text=text,
            prompt_tokens=int(usage.get("input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
            model=str(payload.get("model") or self._model),
        )
