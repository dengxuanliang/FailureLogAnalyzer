from __future__ import annotations
import logging
import orjson
from abc import ABC, abstractmethod
from app.ingestion.schemas import NormalizedRecord

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Subclass this and decorate with @register_adapter("name").
    Subclasses must implement `detect` and `normalize`.
    """

    @abstractmethod
    def detect(self, first_line: str) -> float:
        """Return confidence 0.0–1.0 that this adapter handles the data."""

    @abstractmethod
    def normalize(self, raw: dict) -> NormalizedRecord | None:
        """
        Convert a raw parsed dict to NormalizedRecord.
        Return None to skip the record (e.g. correct answers when loading errors-only).
        """

    def safe_normalize(self, raw: dict) -> NormalizedRecord | None:
        """Call normalize; log and return None on any exception."""
        try:
            return self.normalize(raw)
        except Exception as exc:
            logger.warning(
                "Adapter %s failed on record: %s — %s",
                self.__class__.__name__,
                orjson.dumps(raw)[:200].decode(),
                exc,
            )
            return None
