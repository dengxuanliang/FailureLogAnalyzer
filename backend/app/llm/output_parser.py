"""Parse and validate structured LLM judge responses."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.llm.schemas import LlmJudgeOutput
from app.rules.taxonomy import TaxonomyTree


@dataclass
class LlmParseResult:
    success: bool
    output: LlmJudgeOutput | None = None
    unmatched_tags: list[str] = field(default_factory=list)
    raw_text: str = ""
    error: str = ""


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _strip_code_fence(text: str) -> str:
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_llm_response(raw: str, taxonomy: TaxonomyTree | None = None) -> LlmParseResult:
    """Parse raw LLM response text into a validated output payload."""

    taxonomy = taxonomy or TaxonomyTree.load_default()
    cleaned = _strip_code_fence(raw)

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        return LlmParseResult(success=False, raw_text=raw, error=f"JSON decode error: {exc}")

    try:
        output = LlmJudgeOutput.model_validate(data)
    except ValidationError as exc:
        return LlmParseResult(success=False, raw_text=raw, error=f"Validation error: {exc}")

    unmatched: list[str] = []
    for tag_path in output.error_types:
        if taxonomy.resolve_path(tag_path) is None:
            unmatched.append(tag_path)

    return LlmParseResult(success=True, output=output, unmatched_tags=unmatched, raw_text=raw)
