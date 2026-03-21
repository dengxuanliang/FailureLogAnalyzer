from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.ingestion.adapters  # noqa: F401 — triggers adapter registration
from app.api.v1 import ingest, ws_progress
from app.api.v1.rules import router as rules_router
from app.api.v1.routers import auth, health
from app.api.v1.routers import metrics as metrics_router
from app.api.v1.routers.analysis import router as analysis_router
from app.api.v1.routers.compare import router as compare_router
from app.api.v1.routers.cross_benchmark import router as cross_benchmark_router
from app.api.v1.routers.llm import router as llm_router
from app.api.v1.routers.reports import router as reports_router
from app.api.v1.routers.trends import router as trends_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware import LoggingMiddleware, MetricsMiddleware

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
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(ws_progress.router, prefix="/api/v1", tags=["realtime"])
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(cross_benchmark_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(metrics_router.router, prefix="/api/v1")
