from __future__ import annotations
import orjson
from app.ingestion.adapters.base import BaseAdapter
from app.ingestion.adapters.registry import register_adapter
from app.ingestion.schemas import NormalizedRecord

_KNOWN_FIELDS = frozenset({
    "question_id", "question", "expected_answer", "model_answer",
    "is_correct", "score", "task_category", "extracted_code",
})


@register_adapter("generic_jsonl")
class GenericJsonlAdapter(BaseAdapter):
    """
    Handles any JSONL file that contains at least an `is_correct` field.
    Unknown fields are preserved in `metadata`.
    """

    def detect(self, first_line: str) -> float:
        try:
            obj = orjson.loads(first_line)
        except Exception:
            return 0.0
        if "is_correct" in obj:
            return 0.9
        # Partial match: has question + model_answer
        if "question" in obj and "model_answer" in obj:
            return 0.4
        return 0.0

    def normalize(
        self,
        raw: dict,
        *,
        session_id: str,
        benchmark: str,
        model: str,
        model_version: str,
    ) -> NormalizedRecord | None:
        # Extract known fields; rest goes to metadata
        metadata = {k: v for k, v in raw.items() if k not in _KNOWN_FIELDS}
        return NormalizedRecord(
            session_id=session_id,
            benchmark=benchmark,
            model=model,
            model_version=model_version,
            task_category=raw.get("task_category", ""),
            question_id=str(raw.get("question_id", "")),
            question=str(raw.get("question", "")),
            expected_answer=str(raw.get("expected_answer", "")),
            model_answer=str(raw.get("model_answer", "")),
            is_correct=bool(raw.get("is_correct", False)),
            score=float(raw.get("score", 0.0)),
            extracted_code=str(raw.get("extracted_code", "")),
            metadata=metadata,
            raw_json=raw,
        )
