from app.rules.registry import RuleRegistry
from app.rules.base import BaseRule


def test_all_builtin_rules_registered():
    registry = RuleRegistry.default()
    ids = {r.rule_id for r in registry.all_rules()}
    assert "empty_answer" in ids
    assert "format_mismatch" in ids
    assert "exact_match" in ids
    assert "length_anomaly" in ids
    assert "language_mismatch" in ids
    assert "repetition" in ids
    assert "refusal" in ids
    assert "extracted_field_empty" in ids
    assert "extraction_mismatch" in ids


def test_rules_sorted_by_priority():
    registry = RuleRegistry.default()
    priorities = [r.priority for r in registry.all_rules()]
    assert priorities == sorted(priorities)


def test_filter_by_ids():
    registry = RuleRegistry.default()
    subset = registry.get_rules_by_ids(["empty_answer", "refusal"])
    assert len(subset) == 2
