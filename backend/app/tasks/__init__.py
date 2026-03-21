"""Task package imports for Celery autodiscovery/registration."""

# Import task modules so shared_task decorators register at import time.
from . import analysis, ingest, report  # noqa: F401
