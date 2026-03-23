# FailureLogAnalyzer

FailureLogAnalyzer 是一个用于评测日志摄入、错误分析、版本对比、跨 benchmark 观察与规则/Prompt 配置的全栈应用。

> **当前推荐运行路径**
>
> - **本地演示 / 联调：Docker Compose（推荐）**
> - **Kubernetes：高级部署路径**，需要额外 operator / 预构建镜像；详见 [`k8s/README.md`](k8s/README.md)

## 现实状态 vs 原始 plans

为了保证“现在这个仓库”真正可运行，当前仓库的推荐使用方式与早期 plans 有几点现实差异：

- **本地运行以 `docker compose` 为主**，而不是直接从 k8s dev overlay 起步。
- **Compose 现在覆盖完整演示链路**：Postgres、Redis、API、Celery workers、Frontend。
- **上传能力后端已可用，但前端暂时没有独立上传页面**；本地演示时请先用 API/curl 上传日志。
- **K8s prod 清单仍保留 ingress / cert-manager / monitoring / CNPG backup 等生产资源**；**dev overlay 已改成更保守的“可落地”版本**，会去掉部分可选资源。

## 架构概览

- `frontend/`: React + Vite + Ant Design
- `backend/`: FastAPI + SQLAlchemy async + Alembic
- `postgres`: 主数据存储
- `redis`: Celery broker/backend + 进度事件
- `worker-default`: 处理默认 Celery 队列（**含 ingest/upload 链路**）
- `worker-rule`: 规则分析任务
- `worker-llm`: LLM 分析任务

## 本地依赖

推荐：

- Docker Desktop / Docker Engine + Compose
- `bash`
- 可选：`curl`

如果不走 Compose，本地开发还需要：

- Python **3.11+**
- Node.js **20+**

## 关键环境变量

本地 Compose 主要读取仓库根目录 shell 环境或 `.env` 文件中的变量：

| 变量 | 是否必需 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | 是 | JWT 签名密钥，至少 32 字符 |
| `OPENAI_API_KEY` | 可选 | 只有演示 LLM 分析时需要 |
| `ANTHROPIC_API_KEY` | 可选 | 只有演示 Claude 分析时需要 |
| `CORS_ORIGINS` | 可选 | 默认允许 `http://localhost:3000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 可选 | 默认 `60` |
| `LOG_LEVEL` | 可选 | 默认 `INFO` |

最小可用示例：

```bash
export SECRET_KEY='replace-with-32-chars-minimum-secret'
```

如果要长期本地使用，建议在仓库根目录手动创建 `.env`：

```dotenv
SECRET_KEY=replace-with-32-chars-minimum-secret
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## Podman / Docker 超时修复（当前环境已验证）

如果你的 `docker` CLI 实际上是接到 **Podman machine**，并且在拉取 `docker.io` 镜像时遇到：

- `i/o timeout`
- `Get "https://registry-1.docker.io/v2/" ... timeout`
- `docker compose build` 卡在拉取基础镜像 / buildkit

则优先执行：

```bash
./scripts/podman-enable-dockerhub-mirror.sh
```

这个脚本会：

1. 确保 `pmapple` Podman machine 已启动
2. 在 VM 内把 `docker.io` 重写到可达镜像源
3. 重启 machine 让远端 API 生效
4. 验证：
   - `podman pull docker.io/library/hello-world`
   - `docker run --rm busybox echo docker-ok`

> 说明：这是**当前环境网络现实**下的修复，不是业务代码缺陷。  
> 如果你的宿主网络本身能直接访问 Docker Hub，就不需要这一步。

## 推荐：本地完整演示启动

### 1) 启动整套服务

```bash
docker compose up --build -d
docker compose ps
```

启动后默认端口：

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/api/docs

### 2) 创建演示登录账号

```bash
./scripts/dev-create-admin.sh
```

默认会创建/更新：

- 用户名：`admin`
- 邮箱：`admin@example.com`
- 密码：`admin123456`

如需覆盖：

```bash
DEMO_USERNAME=demo DEMO_EMAIL=demo@example.com DEMO_PASSWORD='StrongerPass123' ./scripts/dev-create-admin.sh
```

> **或：一次性 Bootstrap API（仅在用户表为空时可用）**
>
> 首次启动且数据库没有任何用户时，可以直接调用：
>
> ```bash
> curl -X POST http://localhost:8000/api/v1/auth/bootstrap \
>   -H "Content-Type: application/json" \
>   -d '{"username":"admin","email":"admin@example.com","password":"admin123456"}'
> ```
>
> 一旦已有用户存在，该接口会返回 **409**，不会再创建 bootstrap 管理员。

### 3) 登录前端

打开 http://localhost:3000 ，使用上面的账号登录。

## 演示数据导入（当前推荐方式）

> 当前后端已支持上传与摄入，但前端还没有独立上传页；**演示前请先用 API 上传日志**。

先登录拿到 JWT，再确认可用 adapter：

```bash
curl -s http://localhost:8000/api/v1/ingest/adapters \
  -H "Authorization: Bearer <YOUR_JWT>" | jq .
```

最通用的本地上传格式是 `generic_jsonl`，每行至少建议包含这些字段：

```json
{"question_id":"q1","question":"2+2=?","expected_answer":"4","model_answer":"5","is_correct":false,"score":0,"task_category":"math"}
```

上传示例：

```bash
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -H "Authorization: Bearer <YOUR_JWT>" \
  -F "file=@/absolute/path/to/demo.jsonl" \
  -F "benchmark=demo-benchmark" \
  -F "model=demo-model" \
  -F "model_version=v1" \
  -F "adapter_name=generic_jsonl"
```

然后可用返回的 `job_id` 订阅进度：

```bash
curl -s http://localhost:8000/api/v1/ingest/<job_id>/status | jq .
```

## 推荐演示流程

1. `docker compose up --build -d`
2. `./scripts/dev-create-admin.sh`
3. `./scripts/dev-seed-defaults.sh`（初始化默认 Rules / Strategies / Prompt Templates）
4. `./scripts/dev-seed-demo.sh`（可选：快速生成演示会话/错误数据）
5. 用 API 上传一份 JSONL 日志（或跳过，直接使用 demo seed 数据）
6. 登录前端
7. 演示：
   - Overview
   - Analysis
   - Compare
   - Cross Benchmark
   - Config / Rules / Prompt Templates

如果要演示 LLM 相关能力，再补充：

```bash
export OPENAI_API_KEY=...
# 或
export ANTHROPIC_API_KEY=...
docker compose up -d --build api worker-llm
```

## 常用命令

查看容器：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f api
docker compose logs -f worker-default
docker compose logs -f worker-rule
docker compose logs -f worker-llm
docker compose logs -f frontend
```

停止服务：

```bash
docker compose down
```

连同数据库卷一起清空：

```bash
docker compose down -v
```

## 不走 Compose 的本地开发

只推荐给需要改代码的人。

### 后端

```bash
docker compose up -d postgres redis
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL='postgresql+asyncpg://fla:fla@localhost:5432/fla'
export REDIS_URL='redis://localhost:6379/0'
export SECRET_KEY='replace-with-32-chars-minimum-secret'
alembic upgrade head
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm ci
npm run dev
```

## Kubernetes

Kubernetes 清单位于 `k8s/`，已补齐 base/overlays/monitoring 与部署脚本，但它仍然是：

- **更接近真实集群部署**
- **不适合替代本地演示默认路径**
- **依赖额外 operator / ingress / 镜像仓库**

请先看 [`k8s/README.md`](k8s/README.md)。
