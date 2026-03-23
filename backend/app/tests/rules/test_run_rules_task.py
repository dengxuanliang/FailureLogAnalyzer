"""Unit tests for run_rules task — mock DB, test rule fan-out logic."""
import pytest
from unittest.mock import MagicMock, patch, call
from app.tasks import analysis
from app.tasks.analysis import _apply_rules_to_record
from app.rules.base import RuleContext, RuleResult
from app.rules.registry import RuleRegistry


def _make_record(**kwargs):
    defaults = dict(
        id="record-uuid-1",
        session_id="session-uuid-1",
        model_answer="",
        expected_answer="X",
        question="What is X?",
        extracted_code=None,
        metadata_=None,
    )
    defaults.update(kwargs)
    rec = MagicMock()
    for k, v in defaults.items():
        setattr(rec, k, v)
    return rec


def test_apply_rules_empty_answer():
    registry = RuleRegistry.default()
    record = _make_record(model_answer="")
    results = _apply_rules_to_record(record, registry, session_avg_length=None)
    tag_paths = [r.tag_path for r in results]
    assert "格式与规范错误.空回答/拒绝回答" in tag_paths


def test_apply_rules_normal_answer_no_false_positives():
    registry = RuleRegistry.default()
    record = _make_record(
        model_answer="The answer is Paris.",
        expected_answer="Paris",
        extracted_code=None,
    )
    results = _apply_rules_to_record(record, registry, session_avg_length=20.0)
    # Should not fire empty_answer, refusal, or extraction_mismatch
    tag_paths = [r.tag_path for r in results]
    assert "格式与规范错误.空回答/拒绝回答" not in tag_paths
    assert "生成质量问题.过度对齐" not in tag_paths


def test_apply_rules_returns_list_of_rule_results():
    registry = RuleRegistry.default()
    record = _make_record(model_answer="I'm sorry, I cannot help.")
    results = _apply_rules_to_record(record, registry, session_avg_length=20.0)
    assert isinstance(results, list)
    assert all(isinstance(r, RuleResult) for r in results)


def test_run_rules_logs_start_and_returns_summary():
    expected = {"session_id": "s1", "total_processed": 3, "total_tagged": 2}

    def _run_and_return(coro):
        coro.close()
        return expected

    with patch("app.tasks.analysis.run_async_in_worker", side_effect=_run_and_return) as mock_async_runner, \
         patch("app.tasks.analysis.logger") as mock_logger:
        result = analysis.run_rules.run(session_id="s1", rule_ids=["r1"])

    assert result == expected
    mock_logger.info.assert_any_call("run_rules task started", extra={"session_id": "s1", "rule_ids": ["r1"]})
    assert mock_async_runner.call_count == 1


def test_run_rules_logs_exception_and_retries():
    def _run_and_raise(coro):
        coro.close()
        raise ValueError("boom")

    with patch("app.tasks.analysis.run_async_in_worker", side_effect=_run_and_raise), \
         patch.object(analysis.run_rules, "retry", side_effect=RuntimeError("retry triggered")) as mock_retry, \
         patch("app.tasks.analysis.logger") as mock_logger:
        with pytest.raises(RuntimeError, match="retry triggered"):
            analysis.run_rules.run(session_id="s2", rule_ids=None)

    mock_logger.exception.assert_called_once()
    mock_retry.assert_called_once()
