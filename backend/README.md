# FailureLogAnalyzer Backend

FastAPI + SQLAlchemy async backend.

## Quick Start (Docker)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your SECRET_KEY
docker compose up
```

## Quick Start (Local)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Run Tests

```bash
cd backend
pytest app/tests/unit/ -v
```

## Database Migrations

```bash
cd backend
alembic upgrade head
```
