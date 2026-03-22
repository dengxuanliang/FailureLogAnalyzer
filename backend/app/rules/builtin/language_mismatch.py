import re
from app.rules.base import BaseRule, RuleContext, RuleResult

try:
    from langdetect import detect, LangDetectException
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False

_ZH_TRIGGER = re.compile(r"请用中文|用中文回答|以中文|回答用中文", re.IGNORECASE)
_EN_TRIGGER = re.compile(r"(answer in english|reply in english|in english)", re.IGNORECASE)
_MIN_LEN = 20  # skip detection on very short answers


class LanguageMismatchRule(BaseRule):
    rule_id = "language_mismatch"
    name = "LanguageMismatchRule"
    description = "Detects when answer language does not match the language requested in the question."
    priority = 25

    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        if not _LANGDETECT_AVAILABLE:
            return []
        answer = ctx.model_answer or ""
        if len(answer) < _MIN_LEN:
            return []
        question = ctx.question or ""

        required_lang: str | None = None
        if _ZH_TRIGGER.search(question):
            required_lang = "zh-cn"
        elif _EN_TRIGGER.search(question):
            required_lang = "en"

        if required_lang is None:
            return []

        try:
            detected = detect(answer)
        except LangDetectException:
            return []

        # langdetect returns 'zh-cn' or 'zh-tw' for Chinese
        zh_family = {"zh-cn", "zh-tw"}
        match = (
            (required_lang == "zh-cn" and detected in zh_family)
            or (required_lang == "en" and detected == "en")
        )
        if not match:
            return [RuleResult(
                tag_path="格式与规范错误.语言不匹配",
                confidence=0.85,
                evidence=f"required={required_lang}, detected={detected}",
            )]
        return []
