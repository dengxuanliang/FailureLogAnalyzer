import pytest
from pydantic import ValidationError

from app.llm.prompt_renderer import render_prompt
from app.llm.schemas import LlmJudgeOutput, PromptContext


def test_llm_judge_output_valid():
    output = LlmJudgeOutput(
        error_types=["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
        root_cause="推理链断裂",
        severity="high",
        confidence=0.87,
        evidence="遗漏关键条件",
        suggestion="补充中间推理步骤",
    )

    assert output.severity.value == "high"
    assert output.confidence == pytest.approx(0.87)


def test_llm_judge_output_rejects_invalid_values():
    with pytest.raises(ValidationError):
        LlmJudgeOutput(
            error_types=["x"],
            root_cause="x",
            severity="critical",
            confidence=0.3,
            evidence="x",
            suggestion="x",
        )

    with pytest.raises(ValidationError):
        LlmJudgeOutput(
            error_types=["x"],
            root_cause="x",
            severity="low",
            confidence=2.0,
            evidence="x",
            suggestion="x",
        )


def test_render_prompt_replaces_known_placeholders_and_keeps_unknown():
    template = "Q:{question} E:{expected} A:{model_answer} T:{rule_tags} C:{task_category} X:{unknown}"
    context = PromptContext(
        question="1+1?",
        expected="2",
        model_answer="3",
        rule_tags=["推理性错误.数学/计算错误.算术错误"],
        task_category="math",
    )

    rendered = render_prompt(template, context)

    assert "1+1?" in rendered
    assert "推理性错误.数学/计算错误.算术错误" in rendered
    assert "{question}" not in rendered
    assert "{unknown}" in rendered


def test_render_prompt_uses_defaults_for_empty_fields():
    context = PromptContext(question="q", expected="e", model_answer="a")
    rendered = render_prompt("{rule_tags}|{task_category}", context)

    assert rendered == "(none)|(unknown)"
