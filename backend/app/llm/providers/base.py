"""Provider abstraction for external LLM APIs."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class LlmResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLlmProvider(ABC):
    @abstractmethod
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        """Execute one completion request and normalize the response."""
