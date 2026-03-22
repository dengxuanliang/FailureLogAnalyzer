# FailureLogAnalyzer

大模型评测日志错因分析系统。

> 面向 **评测日志接入、规则归因、LLM 深度判因、版本对比、跨 Benchmark 分析、报告生成** 的全栈工程实现。

## 目录

- [项目概览](#项目概览)
- [核心能力](#核心能力)
- [整体架构](#整体架构)
- [仓库结构](#仓库结构)
- [技术栈](#技术栈)
- [快速开始（推荐）](#快速开始推荐)
- [环境变量说明](#环境变量说明)
- [首次初始化：admin 用户与本地演示数据](#首次初始化admin-用户与本地演示数据)
- [运行方式](#运行方式)
- [使用说明](#使用说明)
- [Demo 演示流程](#demo-演示流程)
- [测试、构建与校验](#测试构建与校验)
- [Docker / Kubernetes 部署说明](#docker--kubernetes-部署说明)
- [已知边界与注意事项](#已知边界与注意事项)

---

## 项目概览

FailureLogAnalyzer 用于分析大模型评测产生的 JSON / JSONL 日志，目标是把“模型为什么错”从原始日志中结构化地提取出来，并通过 Dashboard、Agent 对话和统计图表提供分析、对比和追踪能力。

当前仓库包含：

- **后端 API**：FastAPI + SQLAlchemy async + Alembic + Celery + Redis
- **前端 Dashboard**：React + TypeScript + Vite + Ant Design + ECharts
- **Agent 编排层**：LangGraph Orchestrator
- **部署资产**：Docker Compose + Kubernetes Kustomize manifests

设计文档见：`docs/superpowers/specs/2026-03-18-failure-log-analyzer-design.md`

---

## 核心能力

### 已实现能力

- **日志接入**
  - 支持 `.json` / `.jsonl`
  - 支持单文件上传、目录导入、目录 watcher
  - 流式解析 + 批量写库
  - Redis + WebSocket 进度推送
- **规则分析（Rule Agent）**
  - 内置规则 + 自定义规则
  - 标签化错误归因
  - 分析结果写入 `analysis_results` / `error_tags`
- **LLM Judge（可选）**
  - Prompt Template / Strategy CRUD
  - OpenAI / Claude Provider 抽象
  - 成本统计、限速、熔断、预算控制
- **查询与报表**
  - 总览统计
  - 错因分布
  - 错题明细
  - 版本对比
  - 跨 Benchmark 弱点分析
  - 报告生成任务
- **Agent Chat**
  - REST + WebSocket 对话入口
  - LangGraph 意图识别与任务分发
- **可观测性**
  - `/api/v1/health`
  - Prometheus metrics
  - Kubernetes ServiceMonitor / PrometheusRule

### Dashboard 可见页面

- `/login` 登录页
- `/overview` 总览页
- `/analysis` 错因分析页
- `/compare` 版本对比页
- `/cross-benchmark` 跨 Benchmark 分析页
- `/config` 规则 / 模板 / 策略 / Adapter 配置页

---

## 整体架构

### 架构分层

```mermaid
flowchart TB
    UI[React Dashboard\nAnt Design + ECharts + Agent Chat]
    API[FastAPI REST / WebSocket API]
    AGENT[LangGraph Orchestrator]
    TASKS[Celery Workers\nIngest / Rule / LLM / Report]
    DB[(PostgreSQL)]
    REDIS[(Redis)]
    FILES[JSON / JSONL Logs]

    UI --> API
    API --> AGENT
    API --> TASKS
    AGENT --> TASKS
    TASKS --> DB
    TASKS --> REDIS
    API --> DB
    API --> REDIS
    FILES --> TASKS
```

### 后端主要数据流

1. 用户登录后获得 JWT。
2. 通过 API 上传日志文件或导入目录。
3. Ingestion 任务在 Celery 中执行：
   - 自动识别 Adapter
   - 流式解析原始日志
   - 标准化为 `NormalizedRecord`
   - 批量写入 PostgreSQL
   - 通过 Redis Pub/Sub 推送进度
4. 规则分析或 LLM 分析任务异步执行。
5. Dashboard 通过查询 API 展示总览、对比、热力图、错题详情等。
6. Agent Chat 通过 LangGraph 根据意图触发 query / analyze / compare / report 流程。

### Agent 架构

- **Orchestrator Agent**：`backend/app/agent/graph.py`
- **Intent Router**：`backend/app/agent/intent_router.py`
- **Sub-nodes**：
  - `ingest_node`
  - `analyze_node`
  - `compare_node`
  - `query_node`
  - `report_node`
  - `human_review_node`

### 关键后端模块

| 模块 | 目录 | 作用 |
|---|---|---|
| API 层 | `backend/app/api` | REST / WebSocket 路由 |
| Agent 层 | `backend/app/agent` | LangGraph 编排 |
| Ingestion | `backend/app/ingestion` | 日志解析、标准化、进度推送 |
| Rules | `backend/app/rules` | 规则引擎与分类体系 |
| LLM | `backend/app/llm` | Provider、预算、限速、解析 |
| Service 层 | `backend/app/services` | 汇总查询、对比分析、报告构建 |
| 数据层 | `backend/app/db` | ORM、会话、迁移 |
| 异步任务 | `backend/app/tasks` | Celery 任务实现 |
| Core | `backend/app/core` | 配置、鉴权、Redis、日志、指标 |

### 前端结构

| 模块 | 目录 | 作用 |
|---|---|---|
| App 入口 | `frontend/src/App.tsx` | QueryClient / Auth / Agent Provider 装配 |
| 路由 | `frontend/src/router.tsx` | 登录路由 + 受保护路由 |
| 主布局 | `frontend/src/layouts/AppLayout.tsx` | 左侧导航 + 顶部过滤栏 + Agent Chat |
| 全局过滤器 | `frontend/src/contexts/FilterContext.tsx` | benchmark / model_version / time range |
| API Hooks | `frontend/src/api/queries/*` | React Query 查询与 mutation |
| 页面 | `frontend/src/pages/*` | Overview / Analysis / Compare / CrossBenchmark / Config |

---

## 仓库结构

```text
FailureLogAnalyzer/
├── backend/                      # FastAPI + Celery + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── agent/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── ingestion/
│   │   ├── llm/
│   │   ├── rules/
│   │   ├── services/
│   │   ├── tasks/
│   │   └── tests/
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend/                     # React + TS + Vite Dashboard
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   └── pages/
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── k8s/                          # Kustomize base + overlays
├── scripts/                      # k8s apply / migrate / rollback
├── docker-compose.yml
└── README.md
```

---

## 技术栈

### Backend

- Python 3.11+
- FastAPI
- SQLAlchemy 2 async
- Alembic
- PostgreSQL 15+
- Redis 7+
- Celery
- LangGraph
- Pydantic v2
- Prometheus client

### Frontend

- React 18
- TypeScript 5
- Vite 5
- Ant Design 5
- TanStack React Query 5
- React Router 6
- ECharts 6
- Axios
- i18next

### Deployment

- Docker Compose
- Kubernetes + Kustomize
- CloudNativePG（manifests 中）
- Prometheus Operator（ServiceMonitor / PrometheusRule manifests）

---

## 快速开始（推荐）

> 推荐开发方式：**Postgres / Redis 用 Docker 跑，Backend / Worker / Frontend 本地运行**。这也是当前仓库最容易在新机器上复现的方式。

### 1）准备依赖

请先安装：

- Git
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+（Node 18+ 通常也可运行）
- npm

### 2）克隆仓库

```bash
git clone https://github.com/dengxuanliang/FailureLogAnalyzer.git
cd FailureLogAnalyzer
```

### 3）启动基础依赖（Postgres / Redis）

```bash
docker compose up -d postgres redis
```

确认容器状态：

```bash
docker compose ps
```

### 4）配置并安装 Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

建议把 `backend/.env` 调整为：

```env
DATABASE_URL=postgresql+asyncpg://fla:fla@localhost:5432/fla
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-production-at-least-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
UPLOAD_DIR=/tmp/fla_uploads
# 可选：仅在启用 LLM Judge 时需要
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### 5）执行数据库迁移

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### 6）启动 Backend API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档地址：

- Swagger UI: <http://localhost:8000/api/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

### 7）启动 Celery Worker

另开一个终端：

```bash
cd backend
source .venv/bin/activate
celery -A app.celery_app.celery_app worker -l info -Q celery,rule,llm,report
```

> 不启动 Worker 的话：上传、规则分析、LLM 分析、报告生成等异步能力都不会真正执行；`/api/v1/health` 也会显示 `celery=false`。

### 8）安装并启动 Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

如果你希望显式指定 API 地址，可在 `frontend/.env.local` 中写入：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

然后启动前端：

```bash
cd frontend
npm run dev
```

前端地址：

- Dashboard: <http://localhost:3000>

---

## 环境变量说明

### Backend (`backend/.env`)

| 变量 | 必填 | 默认值 | 说明 |
|---|---:|---|---|
| `DATABASE_URL` | 是 | - | PostgreSQL 连接串 |
| `REDIS_URL` | 是 | `redis://localhost:6379/0` | Redis 连接串 |
| `SECRET_KEY` | 是 | - | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | `60` | JWT 过期时间（分钟） |
| `ENVIRONMENT` | 否 | `development` | 运行环境 |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |
| `CORS_ORIGINS` | 否 | `http://localhost:3000` | 允许的前端来源 |
| `UPLOAD_DIR` | 否 | `/tmp/fla_uploads` | 上传/导入目录根路径 |
| `OPENAI_API_KEY` | 否 | 空 | OpenAI Provider 所需 |
| `ANTHROPIC_API_KEY` | 否 | 空 | Claude Provider 所需 |

### Frontend (`frontend/.env.local`)

| 变量 | 必填 | 默认值 | 说明 |
|---|---:|---|---|
| `VITE_API_BASE_URL` | 否 | `/api/v1` | 前端请求 API 的 base URL |

> 本地开发时，如果通过 Vite dev server 代理访问后端，默认也能工作；显式设置成 `http://localhost:8000/api/v1` 会更直观。

---

## 首次初始化：admin 用户与本地演示数据

当前仓库**没有内置注册接口，也没有提交 demo 用户 seed 脚本**，因此新环境第一次启动后需要先创建一个用户。

### 1）创建管理员用户（推荐）

在 `backend/` 目录执行：

```bash
source .venv/bin/activate
python - <<'PY'
import asyncio
import uuid
from sqlalchemy import select

from app.core.auth import hash_password
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import get_async_session

USERNAME = "admin"
PASSWORD = "admin12345"
EMAIL = "admin@example.com"

async def main():
    async with get_async_session() as db:
        result = await db.execute(select(User).where(User.username == USERNAME))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                id=uuid.uuid4(),
                username=USERNAME,
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(user)
        else:
            user.email = EMAIL
            user.password_hash = hash_password(PASSWORD)
            user.role = UserRole.admin
            user.is_active = True
        await db.commit()
        print(f"ready: {USERNAME} / {PASSWORD}")

asyncio.run(main())
PY
```

创建完成后，你可以用下面账户登录：

- 用户名：`admin`
- 密码：`admin12345`

### 2）准备最小演示日志

在任意目录创建一个 `demo.jsonl`：

```jsonl
{"question_id":"mmlu_math_001","question":"1+1=?","expected_answer":"2","model_answer":"3","is_correct":false,"score":0.0,"task_category":"math/arithmetic"}
{"question_id":"mmlu_json_001","question":"Return JSON only: {\"x\":1}","expected_answer":"{\"x\":1}","model_answer":"x = 1","is_correct":false,"score":0.0,"task_category":"format/json"}
{"question_id":"mmlu_cn_001","question":"请用中文回答：北京是中国的首都吗？","expected_answer":"是","model_answer":"Yes","is_correct":false,"score":0.0,"task_category":"language/chinese"}
```

这个样例足以演示：

- 上传 / 导入
- 错误记录入库
- 规则分析
- Dashboard 总览与分析页查询

---

## 运行方式

### 方式 A：本地开发（推荐）

- Postgres / Redis：Docker
- Backend / Worker / Frontend：本地进程

适合：

- 日常开发
- 调试 API / 前端页面
- 调试 Celery worker

### 方式 B：Docker Compose

仓库根目录的 `docker-compose.yml` 当前包含：

- `postgres`
- `redis`
- `api`

启动方式：

```bash
cp backend/.env.example backend/.env
# 修改 SECRET_KEY

docker compose up --build
```

**注意：** 当前 Compose **不包含 frontend 和 celery worker**。因此它更适合作为“后端基础栈”而不是完整演示栈。

### 方式 C：Kubernetes

见本文后面的 [Docker / Kubernetes 部署说明](#docker--kubernetes-部署说明)。

---

## 使用说明

### 1）登录

打开：<http://localhost:3000>

使用上文创建的管理员账号登录。

### 2）接入日志

当前仓库的接入能力主要通过后端 API 提供：

- `POST /api/v1/ingest/upload`：上传单个 `.json` / `.jsonl`
- `POST /api/v1/ingest/directory`：导入服务器上的目录
- `POST /api/v1/ingest/watcher/start`：启动目录监听
- `GET /api/v1/ingest/adapters`：查看已注册 Adapter
- `WS /api/v1/ws/progress?job_id=<job_id>`：实时进度

> 当前 Dashboard 没有单独的“上传页”，所以**日志接入建议通过 Swagger / curl / Postman 调用 API**。

### 3）规则分析

当前规则分析由 Agent 编排触发，后端实际执行的是 Celery 中的 `run_rules` 任务。

推荐方式：

- 使用 `POST /api/v1/agent/chat`，并显式携带 `session_ids`
- 或在前端中通过 Agent Chat / 相关交互触发

### 4）查看结果

接入并分析后，可以在前端查看：

- **Overview**：总览 KPI + 趋势 + 错因占比
- **Analysis**：Treemap + 错题表格 + 记录详情
- **Compare**：版本间对比与差异摘要
- **Cross Benchmark**：不同 benchmark 的系统性弱点
- **Config**：规则、LLM 模板、策略、Adapter 配置

### 5）启用 LLM Judge（可选）

要真正跑 LLM 分析，需要：

1. 在 `backend/.env` 中填写 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`
2. 启动 Celery worker
3. 在 `/config` 或对应 API 中配置：
   - Prompt Template
   - Analysis Strategy
4. 再触发 LLM 相关任务

相关 API：

- `/api/v1/llm/prompt-templates`
- `/api/v1/llm/strategies`
- `/api/v1/llm/trigger`
- `/api/v1/llm/jobs/trigger`
- `/api/v1/llm/jobs/{job_id}/status`

---

## Demo 演示流程

下面是一套从 0 到可见结果的最小演示流程。

### Step 1：登录获取 token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=admin12345'
```

返回形如：

```json
{"access_token":"<JWT>","token_type":"bearer"}
```

保存 token：

```bash
TOKEN='<你的 JWT>'
```

### Step 2：上传 demo 日志

```bash
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@./demo.jsonl \
  -F benchmark=mmlu \
  -F model=gpt-demo \
  -F model_version=v1
```

返回：

```json
{
  "job_id": "...",
  "session_id": "...",
  "message": "Ingestion job queued"
}
```

请记下：

- `job_id`
- `session_id`

### Step 3：查看上传进度

可轮询：

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/ingest/<job_id>/status
```

或用 WebSocket 订阅：

```text
ws://localhost:8000/api/v1/ws/progress?job_id=<job_id>
```

### Step 4：触发规则分析

```bash
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "分析这批错题",
    "session_ids": ["<session_id>"]
  }'
```

如果 worker 正常运行，后端会派发规则分析任务。

### Step 5：打开 Dashboard 查看成品

- <http://localhost:3000/overview>
- <http://localhost:3000/analysis>
- <http://localhost:3000/compare>
- <http://localhost:3000/cross-benchmark>
- <http://localhost:3000/config>

### Step 6：可选，体验 Agent Chat

登录后右侧会出现 Agent Chat 窗口。你可以尝试：

- `查看分析概览`
- `查看错误分布`
- `对比 v1 和 v2`
- `生成报告`

> 当前 analyze 流程在后端需要明确的 `session_ids` 上下文；如果只给模糊自然语言而没有上下文，可能会收到“请先选择要分析的评测批次”的提示。

---

## 测试、构建与校验

### Backend

```bash
cd backend
source .venv/bin/activate
pytest app/tests -q
```

只跑某类测试：

```bash
pytest app/tests/unit -v
pytest app/tests/api -v
pytest app/tests/llm -v
```

### Frontend

```bash
cd frontend
npm test -- --runInBand
npm run lint
npm run build
```

### 基础健康检查

```bash
curl http://localhost:8000/api/v1/health
```

如果返回中：

- `db=true`
- `redis=true`
- `celery=true`

说明基础栈已基本正常。

---

## Docker / Kubernetes 部署说明

## Docker Compose

当前 `docker-compose.yml` 提供：

- PostgreSQL 15
- Redis 7
- FastAPI API 服务

使用方法：

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

默认端口：

- API：`8000`
- Postgres：`5432`
- Redis：`6379`

> 当前 Compose 未包含前端与 Celery worker，因此如需完整系统，仍需补充这两个进程。

## Kubernetes

### 目录结构

- `k8s/base/`：基础资源
- `k8s/overlays/dev/`：开发环境 overlay
- `k8s/overlays/prod/`：生产环境 overlay

### Base 资源包含

- API deployment/service/hpa/configmap
- Worker（rule / llm）deployment/hpa
- Frontend deployment/service/hpa
- Postgres cluster + backup
- Redis statefulset/service
- Ingress / Certificate
- Monitoring

### Secrets

Kubernetes secrets **不会提交到 Git**，请参考：

- `k8s/base/secrets/README.md`

需要的关键 secret 包括：

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### 一键部署脚本

```bash
./scripts/k8s-apply.sh dev <image_tag>
./scripts/k8s-apply.sh prod <image_tag>
```

脚本会自动：

1. 做 pre-flight checks
2. 设置镜像 tag
3. 执行 dry-run
4. 跑 Alembic migration job
5. apply manifests
6. 等待 rollout 完成
7. 做 API health check

迁移脚本：

```bash
./scripts/k8s-migrate.sh <image_tag> <namespace>
```

回滚脚本：

```bash
./scripts/k8s-rollback.sh <namespace>
```

---

## 已知边界与注意事项

为了让新机器使用者少踩坑，这里把当前仓库的实际边界直接写清楚：

1. **`docker-compose.yml` 不是完整全栈环境**
   - 只有 `postgres`、`redis`、`api`
   - 没有 `frontend`
   - 没有 `celery worker`

2. **首次登录用户需要手动初始化**
   - 当前只有登录接口：`POST /api/v1/auth/login`
   - 没有注册 / bootstrap API
   - README 上方已提供 Python 初始化脚本

3. **日志接入目前主要走 API，不是前端上传页**
   - 后端接入能力完整
   - 前端当前更偏“分析与展示”界面

4. **LLM Judge 依赖真实外部模型密钥**
   - 没有有效 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` 时，相关任务不会真正完成

5. **Kubernetes 清单假设你已经有镜像仓库与镜像构建流程**
   - manifests 中引用的是镜像名
   - 前端镜像构建流程未在当前仓库中完整呈现

6. **前端已预留 Admin 用户管理标签页，但当前仓库快照中未看到对应的 `/api/v1/users` 后端 CRUD 路由**
   - 如需完整用户管理，需要补齐该接口层

7. **Agent analyze 流程当前最稳妥的触发方式是显式传入 `session_ids`**
   - 纯自然语言、无上下文时，可能无法自动定位要分析的评测批次

---

## 参考入口文件

### 设计 / 计划

- `docs/superpowers/specs/2026-03-18-failure-log-analyzer-design.md`
- `docs/superpowers/plans/2026-03-19-01-backend-infrastructure.md`
- `docs/superpowers/plans/2026-03-19-02-ingestion-agent.md`
- `docs/superpowers/plans/2026-03-19-03-rule-agent.md`

### Backend 关键入口

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/celery_app.py`
- `backend/app/api/v1/routers/auth.py`
- `backend/app/api/v1/ingest.py`
- `backend/app/api/v1/routers/llm.py`
- `backend/app/agent/graph.py`

### Frontend 关键入口

- `frontend/src/App.tsx`
- `frontend/src/router.tsx`
- `frontend/src/layouts/AppLayout.tsx`
- `frontend/src/api/client.ts`

### Deployment

- `docker-compose.yml`
- `k8s/base/**`
- `k8s/overlays/**`
- `scripts/k8s-apply.sh`
- `scripts/k8s-migrate.sh`
- `scripts/k8s-rollback.sh`

---

如果你希望我继续补：

- `docs/demo/` 的样例数据
- `docker-compose` 的前端 / worker 补全
- 一键 bootstrap 脚本
- `/api/v1/users` 管理接口

可以直接继续在这个仓库上扩展。
