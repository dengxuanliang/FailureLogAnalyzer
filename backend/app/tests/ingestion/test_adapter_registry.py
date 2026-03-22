import pytest
from app.ingestion.adapters.registry import register_adapter, get_adapter, AdapterRegistry

def test_register_and_retrieve():
    @register_adapter("test_bench")
    class _Adapter:
        def detect(self, first_line: str) -> float:
            return 0.9
        def normalize(self, raw: dict) -> dict:
            return raw

    adapter = get_adapter("test_bench")
    assert adapter is not None
    assert adapter.__class__.__name__ == "_Adapter"

def test_unknown_adapter_returns_none():
    assert get_adapter("does_not_exist_xyz") is None

def test_auto_detect_returns_highest_confidence(tmp_path):
    from app.ingestion.adapters.registry import auto_detect_adapter

    @register_adapter("low_conf")
    class _Low:
        def detect(self, line: str) -> float: return 0.2
        def normalize(self, r: dict) -> dict: return r

    @register_adapter("high_conf")
    class _High:
        def detect(self, line: str) -> float: return 0.95
        def normalize(self, r: dict) -> dict: return r

    f = tmp_path / "sample.jsonl"
    f.write_text('{"is_correct": true}\n')
    result = auto_detect_adapter(str(f))
    assert result is not None
    assert result.__class__.__name__ == "_High"
