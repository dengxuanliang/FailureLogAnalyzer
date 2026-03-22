"""Token-based LLM price estimation."""
from __future__ import annotations

_MODEL_PRICES_PER_1M: dict[str, tuple[float, float]] = {
    # input, output USD per 1M tokens
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-3-5-sonnet": (3.0, 15.0),
}


def _match_model(model: str) -> tuple[float, float] | None:
    normalized = model.lower()
    for prefix, prices in _MODEL_PRICES_PER_1M.items():
        if normalized.startswith(prefix):
            return prices
    return None


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return estimated USD cost for the response. Unknown model => 0."""

    matched = _match_model(model)
    if matched is None:
        return 0.0

    in_price, out_price = matched
    input_cost = prompt_tokens * in_price / 1_000_000
    output_cost = completion_tokens * out_price / 1_000_000
    return input_cost + output_cost
