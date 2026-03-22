from app.rules.base import BaseRule, RuleContext, RuleResult


class EmptyAnswerRule(BaseRule):
    rule_id = "empty_answer"
    name = "EmptyAnswerRule"
    description = "Fires when model_answer is empty or whitespace-only."
    priority = 10

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        if not ctx.model_answer or not ctx.model_answer.strip():
            return [RuleResult(
                tag_path="格式与规范错误.空回答/拒绝回答",
                confidence=0.99,
                evidence="model_answer is empty",
            )]
        return []
