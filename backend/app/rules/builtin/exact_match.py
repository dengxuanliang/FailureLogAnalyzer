from app.rules.base import BaseRule, RuleContext, RuleResult


class ExactMatchRule(BaseRule):
    """Annotates how a correct/incorrect answer relates to the expected answer."""
    rule_id = "exact_match"
    name = "ExactMatchRule"
    description = "Marks whether model_answer exactly matches expected_answer (strict or case-insensitive)."
    priority = 15

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        a = (ctx.model_answer or "").strip()
        e = (ctx.expected_answer or "").strip()
        if not a or not e:
            return []
        if a == e:
            return [RuleResult(
                tag_path="匹配标注.精确匹配",
                confidence=1.0,
                evidence="model_answer == expected_answer (strict)",
            )]
        if a.lower() == e.lower():
            return [RuleResult(
                tag_path="匹配标注.大小写匹配",
                confidence=0.95,
                evidence="model_answer matches expected_answer case-insensitively",
            )]
        return []
