from __future__ import annotations
import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class AdapterProtocol(Protocol):
    def detect(self, first_line: str) -> float:
        """Return confidence 0.0-1.0 that this adapter handles the file."""
        ...

    def normalize(self, raw: dict) -> dict:
        """Map raw record dict to NormalizedRecord field dict."""
        ...


# Module-level registry: name → adapter instance
_REGISTRY: dict[str, AdapterProtocol] = {}

# Expose as AdapterRegistry for import compatibility
AdapterRegistry = _REGISTRY


def register_adapter(name: str):
    """Class decorator that registers an adapter under `name`."""
    def decorator(cls):
        instance = cls()
        _REGISTRY[name] = instance
        logger.debug("Registered adapter %r as %r", cls.__name__, name)
        return cls
    return decorator


def get_adapter(name: str) -> AdapterProtocol | None:
    return _REGISTRY.get(name)


def auto_detect_adapter(file_path: str) -> AdapterProtocol | None:
    """Read first non-empty line and return adapter with highest detect() score."""
    first_line = ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                stripped = raw.strip()
                if stripped:
                    first_line = stripped
                    break
    except OSError as exc:
        logger.warning("auto_detect_adapter: cannot open %s — %s", file_path, exc)
        return None

    best_name, best_score = None, 0.0
    for name, adapter in _REGISTRY.items():
        try:
            score = adapter.detect(first_line)
        except Exception:
            score = 0.0
        if score > best_score:
            best_score = score
            best_name = name

    if best_name is None or best_score == 0.0:
        return None
    return _REGISTRY[best_name]
