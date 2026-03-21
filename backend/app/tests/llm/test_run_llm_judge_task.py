import pytest
from unittest.mock import MagicMock

from app.llm.providers.base import BaseLlmProvider, LlmResponse
from app.tasks.analysis import _FORMAT_REPAIR_SUFFIX, _analyse_single_record


VALID_RESPONSE = '''{
  "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
  "root_cause": "推理链断裂",
  "severity": "high",
  "confidence": 0.9,
  "evidence": "遗漏关键步骤",
  "suggestion": "要求展示中间步骤"
}'''


class StubProvider(BaseLlmProvider):
    def __init__(self, responses: list[LlmResponse]):
        self._responses = responses
        self.calls: list[tuple[str, str]] = []

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        self.calls.append((system_prompt, user_prompt))
        if not self._responses:
            raise RuntimeError("no response configured")
        return self._responses.pop(0)


def _make_record(**kwargs):
    defaults = {
        "id": "record-1",
        "question": "What is 2+2?",
        "expected_answer": "4",
        "model_answer": "5",
        "task_category": "math",
    }
    defaults.update(kwargs)

    record = MagicMock()
    for key, value in defaults.items():
        setattr(record, key, value)
    return record


@pytest.mark.asyncio
async def test_analyse_single_record_success_path():
    provider = StubProvider([
        LlmResponse(
            text=VALID_RESPONSE,
            prompt_tokens=100,
            completion_tokens=50,
            model="gpt-4o",
        )
    ])

    result = await _analyse_single_record(
        record=_make_record(),
        provider=provider,
        template="Q:{question}\nE:{expected}\nA:{model_answer}\nTags:{rule_tags}",
        system_prompt="judge",
        rule_tags=["推理性错误.数学/计算错误.算术错误"],
    )

    assert result["success"] is True
    assert result["error_types"] == ["推理性错误.逻辑推理错误.前提正确但推理链断裂"]
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 50
    assert result["llm_cost"] > 0


@pytest.mark.asyncio
async def test_analyse_single_record_retries_with_format_repair_once_on_parse_failure():
    provider = StubProvider([
        LlmResponse(text="not-json", prompt_tokens=10, completion_tokens=5, model="gpt-4o"),
        LlmResponse(text=VALID_RESPONSE, prompt_tokens=8, completion_tokens=4, model="gpt-4o"),
    ])

    result = await _analyse_single_record(
        record=_make_record(),
        provider=provider,
        template="Q:{question}",
        system_prompt="judge",
        rule_tags=[],
    )

    assert result["success"] is True
    assert len(provider.calls) == 2
    assert provider.calls[-1][1].endswith(_FORMAT_REPAIR_SUFFIX)
    assert result["prompt_tokens"] == 18
    assert result["completion_tokens"] == 9


@pytest.mark.asyncio
async def test_analyse_single_record_returns_failure_when_parse_still_fails():
    provider = StubProvider([
        LlmResponse(text="bad", prompt_tokens=1, completion_tokens=1, model="gpt-4o"),
        LlmResponse(text="still bad", prompt_tokens=2, completion_tokens=3, model="gpt-4o"),
    ])

    result = await _analyse_single_record(
        record=_make_record(),
        provider=provider,
        template="Q:{question}",
        system_prompt="judge",
        rule_tags=[],
    )

    assert result["success"] is False
    assert result["raw_response"] == "still bad"
    assert result["prompt_tokens"] == 3
    assert result["completion_tokens"] == 4
