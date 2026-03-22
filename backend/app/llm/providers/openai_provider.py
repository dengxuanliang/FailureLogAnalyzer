"""OpenAI-compatible provider implementation via HTTP API."""
from __future__ import annotations

from typing import Any

import httpx

from app.llm.providers.base import BaseLlmProvider, LlmResponse


class OpenAIProvider(BaseLlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
        timeout: float = 30.0,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
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
            f"{self._base_url}/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()

        choices = payload.get("choices") or []
        text = ""
        if choices:
            text = choices[0].get("message", {}).get("content") or ""

        usage = payload.get("usage") or {}
        return LlmResponse(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            model=str(payload.get("model") or self._model),
        )
