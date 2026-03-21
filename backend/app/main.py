from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import configure_logging
from app.core.config import settings
from app.api.v1.routers import health, auth
from app.api.v1.routers.analysis import router as analysis_router
from app.api.v1.routers.compare import router as compare_router
from app.api.v1.routers.cross_benchmark import router as cross_benchmark_router
from app.api.v1.routers.trends import router as trends_router
from app.api.v1.routers.reports import router as reports_router
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
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(cross_benchmark_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
