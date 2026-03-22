import json
import re
from app.rules.base import BaseRule, RuleContext, RuleResult

_JSON_TRIGGER = re.compile(r"\b(json|JSON)\b")
_CODE_BLOCK_TRIGGER = re.compile(r"```\w*")


class FormatMismatchRule(BaseRule):
    rule_id = "format_mismatch"
    name = "FormatMismatchRule"
    description = "Fires when question demands JSON/code-block format but answer does not comply."
    priority = 20

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        q = ctx.question or ""
        a = ctx.model_answer or ""

        # JSON required?
        if _JSON_TRIGGER.search(q):
            try:
                json.loads(a)
            except (json.JSONDecodeError, ValueError):
                # Strip markdown fence and retry
                stripped = re.sub(r"^```[a-z]*\n?|```$", "", a.strip(), flags=re.M).strip()
                try:
                    json.loads(stripped)
                except (json.JSONDecodeError, ValueError):
                    return [RuleResult(
                        tag_path="格式与规范错误.输出格式不符",
                        confidence=0.90,
                        evidence="question requires JSON but model_answer is not valid JSON",
                    )]

        # Code block required?
        if _CODE_BLOCK_TRIGGER.search(q) and "```" not in a:
            return [RuleResult(
                tag_path="格式与规范错误.输出格式不符",
                confidence=0.80,
                evidence="question requires code block but model_answer has none",
            )]

        return []
