"""RuleRegistry: collects and resolves rules by ID or priority."""
from __future__ import annotations
from app.rules.base import BaseRule
from app.rules.builtin.empty_answer import EmptyAnswerRule
from app.rules.builtin.format_mismatch import FormatMismatchRule
from app.rules.builtin.exact_match import ExactMatchRule
from app.rules.builtin.length_anomaly import LengthAnomalyRule
from app.rules.builtin.language_mismatch import LanguageMismatchRule
from app.rules.builtin.repetition import RepetitionRule
from app.rules.builtin.refusal import RefusalRule
from app.rules.builtin.extracted_field_empty import ExtractedFieldEmptyRule
from app.rules.builtin.extraction_mismatch import ExtractionMismatchRule

_BUILTIN_RULE_CLASSES: list[type[BaseRule]] = [
    EmptyAnswerRule,
    FormatMismatchRule,
    ExactMatchRule,
    LengthAnomalyRule,
    LanguageMismatchRule,
    RepetitionRule,
    RefusalRule,
    ExtractedFieldEmptyRule,
    ExtractionMismatchRule,
]


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: list[BaseRule] = []

    def register(self, rule: BaseRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def all_rules(self) -> list[BaseRule]:
        return list(self._rules)

    def get_rules_by_ids(self, ids: list[str]) -> list[BaseRule]:
        id_set = set(ids)
        return [r for r in self._rules if r.rule_id in id_set]

    @classmethod
    def default(cls) -> "RuleRegistry":
        registry = cls()
        for rule_cls in _BUILTIN_RULE_CLASSES:
            registry.register(rule_cls())
        return registry
