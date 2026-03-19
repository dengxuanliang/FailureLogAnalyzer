from app.rules.base import BaseRule, RuleContext, RuleResult


class ExtractionMismatchRule(BaseRule):
    rule_id = "extraction_mismatch"
    name = "ExtractionMismatchRule"
    description = "Fires when extracted_code is non-empty but is not a substring of model_answer (extraction error)."
    priority = 45

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        extracted = (ctx.extracted_code or "").strip()
        answer = (ctx.model_answer or "").strip()
        if not extracted or not answer:
            return []
        # Extracted must appear verbatim somewhere inside model_answer
        if extracted not in answer:
            return [RuleResult(
                tag_path="解析类错误.答案提取错误",
                confidence=0.82,
                evidence="extracted_code not found verbatim in model_answer",
            )]
        return []
