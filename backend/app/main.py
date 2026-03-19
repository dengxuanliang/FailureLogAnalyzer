from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import configure_logging
from app.core.config import settings
from app.api.v1.routers import health, auth
from app.api.v1 import ws_progress, ingest
from app.api.v1.rules import router as rules_router
import app.ingestion.adapters  # noqa: F401 — triggers adapter registration

configure_logging()

app = FastAPI(
    title="FailureLogAnalyzer API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(ws_progress.router, prefix="/api/v1", tags=["realtime"])
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
