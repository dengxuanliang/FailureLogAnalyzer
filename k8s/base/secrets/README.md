# Secrets Management

All secrets are created out-of-band (not committed to git).
Use one of these approaches:

## Option A — kubectl (dev / small teams)

```bash
kubectl -n fla create secret generic fla-api \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://fla:<password>@postgres-rw.fla.svc:5432/fla" \
  --from-literal=REDIS_URL="redis://redis.fla.svc:6379/0" \
  --from-literal=OPENAI_API_KEY="sk-..." \
  --from-literal=ANTHROPIC_API_KEY="sk-ant-..."

kubectl -n fla create secret generic fla-postgres \
  --from-literal=username=fla \
  --from-literal=password="$(openssl rand -hex 16)"
```

## Option B — Sealed Secrets (GitOps)

```bash
kubectl -n fla create secret generic fla-api --dry-run=client -o yaml \
  --from-literal=SECRET_KEY="..." | kubeseal -o yaml > k8s/base/secrets/fla-api-sealed.yaml
```

## Option C — External Secrets Operator + AWS Secrets Manager / Vault

Configure `ExternalSecret` resources pointing to your secrets backend.

## Required secret keys

| Secret name  | Keys |
|--------------|------|
| fla-api      | SECRET_KEY, DATABASE_URL, REDIS_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY |
| fla-postgres | username, password (consumed by CloudNativePG Cluster) |
| fla-s3       | ACCESS_KEY_ID, SECRET_ACCESS_KEY (CloudNativePG backups) |
