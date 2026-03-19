import re
from app.rules.base import BaseRule, RuleContext, RuleResult

_REFUSAL_PATTERNS = [
    re.compile(r"(i('m| am) sorry|i cannot|i can't|i am unable to|i'm unable to)", re.I),
    re.compile(r"(as an ai|as a language model).{0,40}(cannot|can't|unable|not able)", re.I),
    re.compile(r"(非常抱歉|很抱歉|我无法|我不能|对不起).{0,20}(回答|提供|帮助|处理)", re.DOTALL),
    re.compile(r"this (request|question|topic) (is|falls) (outside|beyond)", re.I),
    re.compile(r"(不在我的能力范围|超出了我的能力)", re.I),
]


class RefusalRule(BaseRule):
    rule_id = "refusal"
    name = "RefusalRule"
    description = "Detects over-aligned refusal responses."
    priority = 20

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        answer = ctx.model_answer or ""
        for pat in _REFUSAL_PATTERNS:
            if pat.search(answer):
                return [RuleResult(
                    tag_path="生成质量问题.过度对齐",
                    confidence=0.90,
                    evidence=f"matched refusal pattern: {pat.pattern[:60]}",
                )]
        return []
