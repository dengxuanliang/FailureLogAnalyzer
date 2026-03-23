# Kubernetes Deployment Notes

这套 k8s 清单已经补齐到“可审计、可解释、脚本可跑”的状态，但**不是本仓库当前最推荐的演示路径**。  
本地演示请优先使用仓库根目录的 `docker compose`。

## 当前结构

- `base/`
  - API / Frontend / Workers
  - Redis
  - CloudNativePG Postgres Cluster
  - Monitoring 资源
  - Ingress / Certificate（prod 导向）
- `overlays/dev`
  - 命名空间：`fla-dev`
  - 更保守：去掉 ingress/certificate/monitoring/scheduled-backup
  - Postgres 缩成 1 副本并移除对象存储备份
- `overlays/prod`
  - 命名空间：`fla`
  - 保留生产导向资源

## 依赖前提

最少需要：

- Kubernetes 集群
- `kubectl`
- `ruby`（当前 `scripts/k8s-apply.sh` 用它来重写 overlay 中的镜像定义）
- 可访问的镜像仓库
- CloudNativePG（`postgresql.cnpg.io` CRD）

prod overlay 还默认假设存在：

- ingress-nginx
- cert-manager
- Prometheus Operator（`ServiceMonitor` / `PrometheusRule`）
- 对象存储备份凭据（`fla-s3`）

## Secrets

先阅读并创建：

- [`base/secrets/README.md`](base/secrets/README.md)

尤其是：

- `fla-api`
- `fla-postgres`
- `fla-s3`（prod / 需要备份时）

> 注意：`DATABASE_URL` / `REDIS_URL` 需要按目标命名空间填写。  
> `dev` 和 `prod` 不能直接共用写死了 namespace 的 secret 内容。

## 现实差异说明

相对原始 plans，这里有两个现实修正：

1. **新增了 `worker-default`**
   - ingest/upload 任务走默认 Celery 队列 `celery`
   - 如果没有这个 worker，上传链路在 k8s 中会卡住

2. **dev overlay 不再强绑生产资源**
   - cert-manager、ingress、PrometheusRule、ServiceMonitor、ScheduledBackup 已从 dev overlay 剥离
   - 这样更接近“一个普通开发集群真正能 apply 成功”的现实

## 脚本

### 应用 overlay

```bash
./scripts/k8s-apply.sh dev dev
./scripts/k8s-apply.sh prod 2026-03-22
```

可覆盖镜像仓库：

```bash
API_IMAGE_REPO=ghcr.io/your-org/fla-api \
FRONTEND_IMAGE_REPO=ghcr.io/your-org/fla-frontend \
./scripts/k8s-apply.sh prod 2026-03-22
```

### 单独跑 migration job

```bash
./scripts/k8s-migrate.sh 2026-03-22 fla
```

### 回滚

```bash
./scripts/k8s-rollback.sh fla
```

## 推荐的 dev overlay 使用方式

部署：

```bash
./scripts/k8s-apply.sh dev dev
```

然后端口转发：

```bash
kubectl -n fla-dev port-forward svc/api 8000:8000
kubectl -n fla-dev port-forward svc/frontend 3000:80
```

## 推荐的 prod overlay 使用方式

1. 先准备 secrets、镜像、domain、issuer、backup bucket
2. 修改以下占位值：
   - `base/ingress/ingress.yaml`
   - `base/ingress/certificate.yaml`
   - `base/postgres/cluster.yaml`
3. 再执行：

```bash
./scripts/k8s-apply.sh prod <image-tag>
```
