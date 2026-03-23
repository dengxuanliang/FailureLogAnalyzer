# FailureLogAnalyzer Backend

FastAPI + SQLAlchemy async backend.

## Quick Start (Docker)

```bash
cp .env.example .env 2>/dev/null || true
cat > .env <<'EOF'
SECRET_KEY=replace-with-32-chars-minimum-secret
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EOF
docker compose up --build
```

> `docker compose` 读取的是**仓库根目录** shell 环境 / `.env`，不是 `backend/.env`。

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
