from __future__ import annotations
import uuid
import logging
from pathlib import Path
from typing import Annotated

import aiofiles
import aiofiles.os
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.redis import get_redis
from app.api.v1.deps import get_current_user
from app.db.models.user import User
from app.ingestion.directory_watcher import DirectoryWatcher
from app.ingestion.job_store import create_job, get_job_status
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
    model_version: str
    adapter_name: str | None = None
    session_id: str | None = None


class DirectoryResponse(BaseModel):
    session_id: str
    jobs: list[dict]


class WatcherStartRequest(BaseModel):
    watch_dir: str
    benchmark: str = "auto"
    model: str = "unknown"
    model_version: str = "unknown"
    adapter_name: str | None = None
    recursive: bool = True


class WatcherStatusResponse(BaseModel):
    running: bool
    watch_dir: str | None = None


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: Annotated[UploadFile, File()],
    benchmark: Annotated[str, Form()],
    model: Annotated[str, Form()],
    model_version: Annotated[str, Form()],
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
        model_version=model_version,
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
            model_version=body.model_version,
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
        model_version=body.model_version,
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
