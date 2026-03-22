from app.rules.base import BaseRule, RuleContext, RuleResult

_SHORT_RATIO = 0.1   # answer is < 10% of session average → incomplete
_LONG_RATIO = 5.0    # answer is > 5× session average → likely repetition


class LengthAnomalyRule(BaseRule):
    rule_id = "length_anomaly"
    name = "LengthAnomalyRule"
    description = "Flags answers that are anomalously short (incomplete) or long (repetition)."
    priority = 30

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        if ctx.session_avg_length is None or ctx.session_avg_length <= 0:
            return []
        length = len(ctx.model_answer or "")
        ratio = length / ctx.session_avg_length

        if ratio < _SHORT_RATIO:
            return [RuleResult(
                tag_path="生成质量问题.不完整回答",
                confidence=0.75,
                evidence=f"answer length {length} is {ratio:.2%} of session average",
            )]
        if ratio > _LONG_RATIO:
            return [RuleResult(
                tag_path="生成质量问题.重复生成",
                confidence=0.70,
                evidence=f"answer length {length} is {ratio:.1f}× session average",
            )]
        return []
