"""Custom rule loaded from YAML dict or file."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any
import yaml
from app.rules.base import BaseRule, RuleContext, RuleResult


def _get_field_value(ctx: RuleContext, field_path: str) -> Any:
    """Resolve dotted field path against RuleContext.
    Supports top-level attrs and metadata sub-keys, e.g. 'metadata.difficulty'.
    """
    parts = field_path.split(".", 1)
    root = parts[0]
    value = getattr(ctx, root, None)
    if len(parts) == 2 and isinstance(value, dict):
        value = value.get(parts[1])
    return value


class CustomRule(BaseRule):
    """A rule constructed from a YAML/dict definition."""

    def __init__(
        self,
        name: str,
        field_path: str,
        condition: dict,
        tags: list[str],
        confidence: float,
        priority: int = 50,
        description: str = "",
    ) -> None:
        self.rule_id = name
        self.name = name
        self.description = description
        self._field_path = field_path
        self._condition = condition
        self._tags = tags
        self._confidence = confidence
        self.priority = priority

    # ------------------------------------------------------------------

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        value = _get_field_value(ctx, self._field_path)
        if self._matches(value, ctx):
            return [
                RuleResult(tag_path=tag, confidence=self._confidence)
                for tag in self._tags
            ]
        return []

    def _matches(self, value: Any, ctx: RuleContext) -> bool:
        cond = self._condition
        ctype = cond["type"]

        if ctype == "regex":
            return bool(re.search(cond["pattern"], str(value or "")))

        if ctype == "contains":
            return cond["value"] in str(value or "")

        if ctype == "not_contains":
            return cond["value"] not in str(value or "")

        if ctype == "length_gt":
            return len(str(value or "")) > int(cond["value"])

        if ctype == "length_lt":
            return len(str(value or "")) < int(cond["value"])

        if ctype == "field_equals":
            return value == cond["value"]

        if ctype == "field_missing":
            return value is None or value == ""

        if ctype == "python_expr":
            # Sandboxed eval — only `value` and `ctx` are in scope.
            # SECURITY NOTE: only Analyst/Admin users may create python_expr rules.
            try:
                return bool(eval(cond["expr"], {"__builtins__": {"len": len, "str": str, "int": int, "float": float, "bool": bool}}, {"value": value, "ctx": ctx}))  # noqa: S307
            except Exception:
                return False

        raise ValueError(f"Unknown condition type: {ctype!r}")

    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "CustomRule":
        return cls(
            name=data["name"],
            field_path=data.get("field", "model_answer"),
            condition=data["condition"],
            tags=data.get("tags", []),
            confidence=float(data.get("confidence", 0.8)),
            priority=int(data.get("priority", 50)),
            description=data.get("description", ""),
        )


class CustomRuleEngine:
    """Loads and runs a collection of custom rules."""

    def __init__(self, rules: list[CustomRule]) -> None:
        self.rules = sorted(rules, key=lambda r: r.priority)

    def evaluate_all(self, ctx: RuleContext) -> list[RuleResult]:
        results: list[RuleResult] = []
        for rule in self.rules:
            results.extend(rule.evaluate(ctx))
        return results

    @classmethod
    def from_yaml_file(cls, path: str) -> "CustomRuleEngine":
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        rules = [CustomRule.from_dict(r) for r in data.get("rules", [])]
        return cls(rules=rules)

    @classmethod
    def from_yaml_string(cls, text: str) -> "CustomRuleEngine":
        data = yaml.safe_load(text)
        rules = [CustomRule.from_dict(r) for r in data.get("rules", [])]
        return cls(rules=rules)
