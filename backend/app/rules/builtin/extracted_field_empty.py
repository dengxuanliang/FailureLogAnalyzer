from app.rules.base import BaseRule, RuleContext, RuleResult


class ExtractedFieldEmptyRule(BaseRule):
    rule_id = "extracted_field_empty"
    name = "ExtractedFieldEmptyRule"
    description = "Fires when extracted_code is empty/None but model_answer is non-empty (extraction failure)."
    priority = 40

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        has_answer = bool(ctx.model_answer and ctx.model_answer.strip())
        has_extracted = bool(ctx.extracted_code and ctx.extracted_code.strip())
        if has_answer and not has_extracted:
            return [RuleResult(
                tag_path="解析类错误.代码提取为空",
                confidence=0.88,
                evidence="model_answer non-empty but extracted_code is empty",
            )]
        return []
