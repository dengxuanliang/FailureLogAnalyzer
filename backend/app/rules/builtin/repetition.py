from collections import Counter
from app.rules.base import BaseRule, RuleContext, RuleResult

_MIN_TOKENS = 30
_NGRAM_N = 3
_REPETITION_THRESHOLD = 0.5  # > 50% of n-grams are duplicates → repetition


def _ngram_repetition_rate(tokens: list[str], n: int) -> float:
    """Fraction of n-grams that are duplicates."""
    if len(tokens) < n:
        return 0.0
    ngrams = [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    total = len(ngrams)
    unique = len(set(ngrams))
    return 1.0 - (unique / total)


class RepetitionRule(BaseRule):
    rule_id = "repetition"
    name = "RepetitionRule"
    description = "Detects repetitive generation via n-gram overlap."
    priority = 35

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        tokens = (ctx.model_answer or "").split()
        if len(tokens) < _MIN_TOKENS:
            return []
        rate = _ngram_repetition_rate(tokens, _NGRAM_N)
        if rate > _REPETITION_THRESHOLD:
            return [RuleResult(
                tag_path="生成质量问题.重复生成",
                confidence=min(0.95, 0.5 + rate),
                evidence=f"{_NGRAM_N}-gram repetition rate = {rate:.2%}",
            )]
        return []
