# Auto-import all adapters so their @register_adapter decorators execute
from app.ingestion.adapters import generic_jsonl  # noqa: F401
