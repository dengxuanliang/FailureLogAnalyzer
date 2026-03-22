"""Template renderer for LLM judge prompts."""
from __future__ import annotations

from app.llm.schemas import PromptContext


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_prompt(template: str, ctx: PromptContext) -> str:
    """Render known placeholders and keep unknown placeholders untouched."""

    values = _SafeFormatDict(
        question=ctx.question,
        expected=ctx.expected,
        model_answer=ctx.model_answer,
        rule_tags=", ".join(ctx.rule_tags) if ctx.rule_tags else "(none)",
        task_category=ctx.task_category or "(unknown)",
    )
    return template.format_map(values)
