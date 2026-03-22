import pytest

from app.llm.cost_calculator import estimate_cost


def test_estimate_cost_for_gpt_4o():
    cost = estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    expected = (1000 * 2.5 / 1_000_000) + (500 * 10.0 / 1_000_000)

    assert cost == pytest.approx(expected)


def test_unknown_model_cost_is_zero():
    assert estimate_cost("unknown", 100, 100) == 0.0
