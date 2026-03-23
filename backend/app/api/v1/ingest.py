from __future__ import annotations
import uuid
import logging
from pathlib import Path
from typing import Annotated

import aiofiles
import aiofiles.os
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.redis import get_redis
from app.api.v1.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_async_session
from app.ingestion.directory_watcher import DirectoryWatcher
from app.ingestion.adapters.registry import AdapterRegistry
from app.ingestion.job_store import create_job, get_job_status, list_jobs
from app.ingestion.session_store import ensure_eval_session
from app.tasks.ingest import parse_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

_ALLOWED_EXTENSIONS = {".jsonl", ".json"}
_UPLOAD_DIR = Path(settings.UPLOAD_DIR)  # e.g. /tmp/fla_uploads
_active_watcher: DirectoryWatcher | None = None


async def save_upload_file(upload: UploadFile, dest_dir: Path) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(upload.filename or "upload.jsonl").name
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await upload.read(1024 * 1024):  # 1 MB chunks
            await out.write(chunk)
    return str(dest)


class UploadResponse(BaseModel):
    job_id: str
    session_id: str
    message: str


class DirectoryRequest(BaseModel):
    directory_path: str
    benchmark: str
    model: str
    version: str = Field(alias="model_version")
    adapter_name: str | None = None
    session_id: str | None = None


class DirectoryResponse(BaseModel):
    session_id: str
    jobs: list[dict]


class IngestJobListItem(BaseModel):
    job_id: str
    session_id: str
    file_path: str
    status: str
    processed: int = 0
    total: int | None = None
    total_written: int = 0
    total_skipped: int = 0
    created_at: float
    reason: str = ""


class IngestJobListResponse(BaseModel):
    items: list[IngestJobListItem]
    total: int


class WatcherStartRequest(BaseModel):
    watch_dir: str
    benchmark: str = "auto"
    model: str = "unknown"
    version: str = Field(default="unknown", alias="model_version")
    adapter_name: str | None = None
    recursive: bool = True


class WatcherStatusResponse(BaseModel):
    running: bool
    watch_dir: str | None = None


class AdapterMetadata(BaseModel):
    name: str
    description: str
    detected_fields: list[str]
    is_builtin: bool


@router.get("/adapters", response_model=list[AdapterMetadata])
async def list_adapters(
    _: User = Depends(get_current_user),
) -> list[AdapterMetadata]:
    items: list[AdapterMetadata] = []
    for name, adapter in sorted(AdapterRegistry.items()):
        cls = adapter.__class__
        description = (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else name
        detected_fields = getattr(cls, "DETECTED_FIELDS", None)
        if not isinstance(detected_fields, (list, tuple, set)):
            detected_fields = []
        items.append(
            AdapterMetadata(
                name=name,
                description=description or name,
                detected_fields=[str(field) for field in detected_fields],
                is_builtin=cls.__module__.startswith("app.ingestion.adapters"),
            )
        )
    return items


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: Annotated[UploadFile, File()],
    benchmark: Annotated[str, Form()],
    model: Annotated[str, Form()],
    version: Annotated[str, Form(alias="model_version")],
    adapter_name: Annotated[str | None, Form()] = None,
    session_id: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """
    POST /api/v1/ingest/upload
    Upload a single .json or .jsonl file for ingestion.
    Returns job_id for progress tracking via WS /api/v1/ws/progress?job_id=<id>.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File must be .json or .jsonl, got {suffix!r}",
        )

    job_id = str(uuid.uuid4())
    resolved_session_id = session_id or str(uuid.uuid4())

    file_path = await save_upload_file(file, _UPLOAD_DIR / resolved_session_id)

    try:
        async with get_async_session() as db_session:
            await ensure_eval_session(
                session=db_session,
                session_id=resolved_session_id,
                benchmark=benchmark,
                model=model,
                model_version=version,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"session_id must be a UUID: {exc}",
        ) from exc

    redis = await get_redis()
    await create_job(
        redis, job_id=job_id, session_id=resolved_session_id, file_path=file_path
    )

    parse_file.delay(
        file_path,
        adapter_name=adapter_name,
        job_id=job_id,
        session_id=resolved_session_id,
        benchmark=benchmark,
        model=model,
        model_version=version,
    )

    return UploadResponse(
        job_id=job_id,
        session_id=resolved_session_id,
        message="Ingestion job queued",
    )


@router.post("/directory", response_model=DirectoryResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_directory(
    body: DirectoryRequest,
    current_user: User = Depends(get_current_user),
) -> DirectoryResponse:
    """
    POST /api/v1/ingest/directory
    Scan a server-side directory and queue one Celery task per .json/.jsonl file.
    """
    dir_path = Path(body.directory_path)
    base = Path(settings.UPLOAD_DIR).resolve()
    resolved = dir_path.resolve()
    if not str(resolved).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Directory must be within upload root")
    if not dir_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Not a directory: {body.directory_path}",
        )

    files = [
        f for f in dir_path.iterdir()
        if f.suffix.lower() in _ALLOWED_EXTENSIONS
    ]
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No .json or .jsonl files found in directory",
        )

    session_id = body.session_id or str(uuid.uuid4())
    try:
        async with get_async_session() as db_session:
            await ensure_eval_session(
                session=db_session,
                session_id=session_id,
                benchmark=body.benchmark,
                model=body.model,
                model_version=body.version,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"session_id must be a UUID: {exc}",
        ) from exc

    redis = await get_redis()
    jobs = []

    for file_path in files:
        job_id = str(uuid.uuid4())
        await create_job(
            redis, job_id=job_id, session_id=session_id, file_path=str(file_path)
        )
        parse_file.delay(
            str(file_path),
            adapter_name=body.adapter_name,
            job_id=job_id,
            session_id=session_id,
            benchmark=body.benchmark,
            model=body.model,
            model_version=body.version,
        )
        jobs.append({"job_id": job_id, "file": file_path.name})

    return DirectoryResponse(session_id=session_id, jobs=jobs)


@router.post("/watcher/start", response_model=WatcherStatusResponse)
async def start_watcher(
    body: WatcherStartRequest,
    current_user: User = Depends(get_current_user),
) -> WatcherStatusResponse:
    global _active_watcher
    if _active_watcher and _active_watcher.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Watcher is already running",
        )

    _active_watcher = DirectoryWatcher(
        watch_dir=body.watch_dir,
        benchmark=body.benchmark,
        model=body.model,
        model_version=body.version,
        adapter_name=body.adapter_name,
        recursive=body.recursive,
    )
    _active_watcher.start()
    return WatcherStatusResponse(running=True, watch_dir=body.watch_dir)


@router.post("/watcher/stop", response_model=WatcherStatusResponse)
async def stop_watcher(
    current_user: User = Depends(get_current_user),
) -> WatcherStatusResponse:
    global _active_watcher
    if not _active_watcher or not _active_watcher.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No watcher is running",
        )

    _active_watcher.stop()
    _active_watcher = None
    return WatcherStatusResponse(running=False)


@router.get("/watcher/status", response_model=WatcherStatusResponse)
async def watcher_status(
    current_user: User = Depends(get_current_user),
) -> WatcherStatusResponse:
    if _active_watcher and _active_watcher.is_running:
        return WatcherStatusResponse(
            running=True,
            watch_dir=str(_active_watcher.watch_dir),
        )
    return WatcherStatusResponse(running=False)


@router.get("/{job_id}/status")
async def get_ingest_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    GET /api/v1/ingest/{job_id}/status
    Poll ingestion job status (alternative to WebSocket).
    """
    redis = await get_redis()
    job = await get_job_status(redis, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id!r} not found",
        )
    return job


@router.get("/jobs", response_model=IngestJobListResponse)
async def list_ingest_jobs(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    session_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> IngestJobListResponse:
    redis = await get_redis()
    jobs, total = await list_jobs(
        redis,
        limit=limit,
        offset=offset,
        status=status_filter,
        session_id=session_id,
    )
    items = [IngestJobListItem(**job) for job in jobs]
    return IngestJobListResponse(items=items, total=total)
