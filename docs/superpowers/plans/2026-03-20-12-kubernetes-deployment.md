# Kubernetes Production Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide production-grade Kubernetes manifests for all FailureLogAnalyzer services (API, Celery Worker, Frontend, PostgreSQL via CloudNativePG operator, Redis Sentinel), with Horizontal Pod Autoscaling, Ingress TLS termination, Secrets management, and health-gate rollout strategy — as specified in design doc §10.2.

**Architecture:**

```
Ingress (TLS) ──► Service/api       ──► Deployment/api        (HPA: 2-10 pods)
                ──► Service/frontend  ──► Deployment/frontend   (HPA: 1-4 pods)
                                        Deployment/worker-rule  (HPA: 1-8 pods)
                                        Deployment/worker-llm   (HPA: 1-20 pods, LLM API concurrency limit)
                                        StatefulSet via CloudNativePG Cluster CRD
                                        StatefulSet/redis-sentinel (3 pods)
```

**Design doc reference:** §10.2 Kubernetes（生产/可扩展）

**Tech Stack:** Kubernetes 1.29+, Helm 3 (dependencies only), CloudNativePG operator, NGINX Ingress Controller, cert-manager (TLS), Kustomize (env overlays), SOPS / Sealed Secrets (secrets encryption)

**Prerequisites:** Plan 01 complete (Docker images buildable from `backend/Dockerfile`), Plan 07 complete (frontend buildable). Images pushed to a container registry (e.g. `ghcr.io/org/fla-api`, `ghcr.io/org/fla-frontend`).

---

## File Structure After This Plan

```
k8s/
  base/
    namespace.yaml
    api/
      deployment.yaml
      service.yaml
      hpa.yaml
      configmap.yaml
    worker/
      deployment-rule.yaml     # Rule Engine worker
      deployment-llm.yaml      # LLM Judge worker (separate HPA limits)
      hpa-rule.yaml
      hpa-llm.yaml
    frontend/
      deployment.yaml
      service.yaml
      hpa.yaml
    postgres/
      cluster.yaml             # CloudNativePG Cluster CRD
      scheduled-backup.yaml    # CloudNativePG ScheduledBackup CRD
    redis/
      statefulset.yaml         # Redis Sentinel (3-node)
      service-headless.yaml
      service.yaml
      configmap.yaml
    ingress/
      ingress.yaml
      certificate.yaml         # cert-manager Certificate CRD
    secrets/
      README.md                # How to create secrets (never commit plaintext)
    kustomization.yaml
  overlays/
    dev/
      kustomization.yaml       # patch: 1 replica, no HPA, local registry
      patches/
        api-replicas.yaml
        worker-replicas.yaml
    prod/
      kustomization.yaml       # patch: resource limits, node affinity
      patches/
        api-resources.yaml
        worker-llm-resources.yaml
scripts/
  k8s-apply.sh                 # apply base + overlay with pre-flight checks
  k8s-migrate.sh               # run alembic upgrade head in a Job
  k8s-rollback.sh              # annotate rollout history + rollback
```

---

## Task 1 — Namespace & Common Labels

**Files:**
- Create: `k8s/base/namespace.yaml`
- Create: `k8s/base/kustomization.yaml`

### Steps

- [ ] **Step 1: Create `k8s/base/namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fla
  labels:
    app.kubernetes.io/part-of: failure-log-analyzer
```

- [ ] **Step 2: Create `k8s/base/kustomization.yaml`**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: fla

commonLabels:
  app.kubernetes.io/part-of: failure-log-analyzer
  app.kubernetes.io/managed-by: kustomize

resources:
  - namespace.yaml
  - api/deployment.yaml
  - api/service.yaml
  - api/hpa.yaml
  - api/configmap.yaml
  - worker/deployment-rule.yaml
  - worker/deployment-llm.yaml
  - worker/hpa-rule.yaml
  - worker/hpa-llm.yaml
  - frontend/deployment.yaml
  - frontend/service.yaml
  - frontend/hpa.yaml
  - postgres/cluster.yaml
  - postgres/scheduled-backup.yaml
  - redis/statefulset.yaml
  - redis/service-headless.yaml
  - redis/service.yaml
  - redis/configmap.yaml
  - ingress/ingress.yaml
  - ingress/certificate.yaml
```

- [ ] **Step 3: Validate**
  ```bash
  kubectl kustomize k8s/base --dry-run
  ```
  Expected: renders all resources without error.

---

## Task 2 — Secrets Strategy

**Files:**
- Create: `k8s/base/secrets/README.md`

### Steps

- [ ] **Step 1: Document secrets — never commit plaintext values**

```markdown
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
# Install kubeseal CLI
# Encrypt:
kubectl -n fla create secret generic fla-api --dry-run=client -o yaml \
  --from-literal=SECRET_KEY="..." | kubeseal -o yaml > k8s/base/secrets/fla-api-sealed.yaml
```

## Option C — External Secrets Operator + AWS Secrets Manager / Vault

Configure ExternalSecret CRD pointing to your secrets backend.

## Required secret keys

| Secret name   | Keys |
|---------------|------|
| fla-api       | SECRET_KEY, DATABASE_URL, REDIS_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY |
| fla-postgres  | username, password (consumed by CloudNativePG Cluster) |
```

- [ ] Commit: `git commit -m "docs(k8s): add secrets management README"`

---

## Task 3 — API Deployment + Service + ConfigMap + HPA

**Files:**
- Create: `k8s/base/api/configmap.yaml`
- Create: `k8s/base/api/deployment.yaml`
- Create: `k8s/base/api/service.yaml`
- Create: `k8s/base/api/hpa.yaml`

### Steps

- [ ] **Step 1: `k8s/base/api/configmap.yaml`** — non-secret env vars

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fla-api-config
data:
  ENVIRONMENT: production
  ACCESS_TOKEN_EXPIRE_MINUTES: "60"
  LOG_LEVEL: INFO
  # DB read/write service name provided by CloudNativePG
  DB_HOST: postgres-rw.fla.svc.cluster.local
  DB_PORT: "5432"
  DB_NAME: fla
  REDIS_HOST: redis.fla.svc.cluster.local
  REDIS_PORT: "6379"
```

- [ ] **Step 2: `k8s/base/api/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels:
    app.kubernetes.io/name: api
    app.kubernetes.io/component: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0          # zero-downtime rollout
  template:
    metadata:
      labels:
        app.kubernetes.io/name: api
        app.kubernetes.io/component: api
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: api
          image: ghcr.io/org/fla-api:latest  # override per overlay
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: fla-api-config
            - secretRef:
                name: fla-api
          env:
            # Construct DATABASE_URL from components (override SECRET if needed)
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: fla-postgres
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: fla-postgres
                  key: password
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 20
            periodSeconds: 30
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["sh", "-c", "sleep 5"]  # drain in-flight requests
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app.kubernetes.io/name: api
                topologyKey: kubernetes.io/hostname
```

- [ ] **Step 3: `k8s/base/api/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector:
    app.kubernetes.io/name: api
  ports:
    - name: http
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

- [ ] **Step 4: `k8s/base/api/hpa.yaml`**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 120   # prevent flapping
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
```

---

## Task 4 — Celery Workers (Rule + LLM, separate HPAs)

**Files:**
- Create: `k8s/base/worker/deployment-rule.yaml`
- Create: `k8s/base/worker/deployment-llm.yaml`
- Create: `k8s/base/worker/hpa-rule.yaml`
- Create: `k8s/base/worker/hpa-llm.yaml`

### Steps

**Design rationale:** The Rule Engine worker is CPU-bound and scales on CPU utilization. The LLM Judge worker is I/O-bound (external API calls) and is intentionally limited in replica count to respect LLM API concurrency limits (§6.4 of design doc: `max_concurrent` per strategy).

- [ ] **Step 1: `k8s/base/worker/deployment-rule.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-rule
  labels:
    app.kubernetes.io/name: worker-rule
    app.kubernetes.io/component: worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: worker-rule
  template:
    metadata:
      labels:
        app.kubernetes.io/name: worker-rule
        app.kubernetes.io/component: worker
    spec:
      terminationGracePeriodSeconds: 60   # allow current task to finish
      containers:
        - name: worker-rule
          image: ghcr.io/org/fla-api:latest
          command:
            - celery
            - -A
            - app.celery_app
            - worker
            - --queues=rule
            - --concurrency=4
            - --loglevel=info
            - --without-gossip
            - --without-mingle
          envFrom:
            - configMapRef:
                name: fla-api-config
            - secretRef:
                name: fla-api
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 1Gi
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - celery -A app.celery_app inspect ping -d celery@$HOSTNAME
            initialDelaySeconds: 30
            periodSeconds: 60
            failureThreshold: 3
```

- [ ] **Step 2: `k8s/base/worker/deployment-llm.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-llm
  labels:
    app.kubernetes.io/name: worker-llm
    app.kubernetes.io/component: worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: worker-llm
  template:
    metadata:
      labels:
        app.kubernetes.io/name: worker-llm
        app.kubernetes.io/component: worker
    spec:
      terminationGracePeriodSeconds: 120  # LLM calls can take longer
      containers:
        - name: worker-llm
          image: ghcr.io/org/fla-api:latest
          command:
            - celery
            - -A
            - app.celery_app
            - worker
            - --queues=llm
            - --concurrency=2          # match LLM API concurrency limit
            - --loglevel=info
            - --without-gossip
            - --without-mingle
          envFrom:
            - configMapRef:
                name: fla-api-config
            - secretRef:
                name: fla-api
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - celery -A app.celery_app inspect ping -d celery@$HOSTNAME
            initialDelaySeconds: 30
            periodSeconds: 60
            failureThreshold: 3
```

- [ ] **Step 3: `k8s/base/worker/hpa-rule.yaml`**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-rule
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: worker-rule
  minReplicas: 1
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # don't scale down mid-batch
```

- [ ] **Step 4: `k8s/base/worker/hpa-llm.yaml`**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-llm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: worker-llm
  minReplicas: 1
  maxReplicas: 20   # upper bound set by LLM API rate limit plan
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 180
    scaleUp:
      stabilizationWindowSeconds: 15    # scale up fast for burst LLM requests
```

---

## Task 5 — Frontend Deployment + Service + HPA

**Files:**
- Create: `k8s/base/frontend/deployment.yaml`
- Create: `k8s/base/frontend/service.yaml`
- Create: `k8s/base/frontend/hpa.yaml`

### Steps

- [ ] **Step 1: `k8s/base/frontend/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  labels:
    app.kubernetes.io/name: frontend
    app.kubernetes.io/component: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: frontend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: frontend
        app.kubernetes.io/component: frontend
    spec:
      containers:
        - name: frontend
          image: ghcr.io/org/fla-frontend:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 80
              name: http
          env:
            - name: VITE_API_BASE_URL
              value: /api/v1       # relative — Ingress rewrites to api service
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
```

- [ ] **Step 2: `k8s/base/frontend/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app.kubernetes.io/name: frontend
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

- [ ] **Step 3: `k8s/base/frontend/hpa.yaml`**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
```

---

## Task 6 — PostgreSQL via CloudNativePG

**Files:**
- Create: `k8s/base/postgres/cluster.yaml`
- Create: `k8s/base/postgres/scheduled-backup.yaml`

### Steps

**Design rationale:** CloudNativePG manages HA PostgreSQL natively in Kubernetes: primary/replica failover, streaming replication, connection pooling via PgBouncer, and S3-compatible WAL archiving. The `Cluster` CRD creates separate read/write (`postgres-rw`) and read-only (`postgres-ro`) Services — the API Deployment uses `postgres-rw`, the query-heavy report workers can use `postgres-ro`.

- [ ] **Step 1: Install CloudNativePG operator (run once per cluster)**
  ```bash
  kubectl apply --server-side -f \
    https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.0.yaml
  # Verify:
  kubectl -n cnpg-system get pods
  ```

- [ ] **Step 2: `k8s/base/postgres/cluster.yaml`**

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres
spec:
  instances: 3                   # 1 primary + 2 replicas

  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      work_mem: "16MB"
      maintenance_work_mem: "128MB"
      wal_level: logical          # required for logical replication / CDC
      max_wal_senders: "10"

  storage:
    size: 50Gi
    storageClass: standard        # replace with your storage class

  superuserSecret:
    name: fla-postgres            # uses username/password keys

  bootstrap:
    initdb:
      database: fla
      owner: fla
      secret:
        name: fla-postgres

  monitoring:
    enablePodMonitor: true        # emits Prometheus metrics if PodMonitor CRD exists

  # Connection pooler (PgBouncer) for API pods
  pooler:
    type: rw
    instances: 2
    pgbouncer:
      poolMode: transaction
      parameters:
        max_client_conn: "400"
        default_pool_size: "20"

  backup:
    retentionPolicy: 7d
    barmanObjectStore:
      destinationPath: s3://your-bucket/postgres-backups/  # update per env
      s3Credentials:
        accessKeyId:
          name: fla-s3
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: fla-s3
          key: SECRET_ACCESS_KEY
```

> **Note:** Replace `s3://your-bucket/...` with actual bucket path. For dev overlay, comment out `barmanObjectStore` to skip S3 backup.

- [ ] **Step 3: `k8s/base/postgres/scheduled-backup.yaml`**

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: postgres-daily
spec:
  schedule: "0 2 * * *"          # 02:00 UTC daily
  cluster:
    name: postgres
  backupOwnerReference: self
  immediate: false
```

- [ ] **Step 4: Verify cluster starts**
  ```bash
  kubectl -n fla get cluster postgres
  # Expected: STATUS=Cluster in healthy state, 3/3 instances
  kubectl -n fla get pods -l cnpg.io/cluster=postgres
  ```

---

## Task 7 — Redis Sentinel

**Files:**
- Create: `k8s/base/redis/configmap.yaml`
- Create: `k8s/base/redis/statefulset.yaml`
- Create: `k8s/base/redis/service-headless.yaml`
- Create: `k8s/base/redis/service.yaml`

### Steps

**Design rationale:** A 3-pod Redis Sentinel setup provides HA without requiring Redis Cluster (which needs 6 pods). Sentinel handles leader election and auto-failover. Celery and LangGraph Checkpointer connect to the Sentinel endpoint; on failover, they reconnect to the new primary automatically.

- [ ] **Step 1: `k8s/base/redis/configmap.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  redis.conf: |
    save 900 1
    save 300 10
    appendonly yes
    appendfsync everysec
    maxmemory 512mb
    maxmemory-policy allkeys-lru

  sentinel.conf: |
    sentinel monitor fla-master redis-0.redis-headless.fla.svc.cluster.local 6379 2
    sentinel down-after-milliseconds fla-master 5000
    sentinel failover-timeout fla-master 60000
    sentinel parallel-syncs fla-master 1
```

- [ ] **Step 2: `k8s/base/redis/statefulset.yaml`**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
spec:
  serviceName: redis-headless
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/name: redis
  template:
    metadata:
      labels:
        app.kubernetes.io/name: redis
        app.kubernetes.io/component: cache
    spec:
      initContainers:
        - name: init-redis
          image: redis:7-alpine
          command:
            - sh
            - -c
            - |
              # Copy config and replace placeholder with actual pod-0 address
              cp /mnt/config/redis.conf /data/redis.conf
              cp /mnt/config/sentinel.conf /data/sentinel.conf
          volumeMounts:
            - name: config
              mountPath: /mnt/config
            - name: data
              mountPath: /data
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server", "/data/redis.conf"]
          ports:
            - containerPort: 6379
              name: redis
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 15
            periodSeconds: 20
          volumeMounts:
            - name: data
              mountPath: /data
        - name: sentinel
          image: redis:7-alpine
          command: ["redis-sentinel", "/data/sentinel.conf"]
          ports:
            - containerPort: 26379
              name: sentinel
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: config
          configMap:
            name: redis-config
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
```

- [ ] **Step 3: `k8s/base/redis/service-headless.yaml`** (stable DNS for StatefulSet)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-headless
spec:
  selector:
    app.kubernetes.io/name: redis
  clusterIP: None
  ports:
    - name: redis
      port: 6379
    - name: sentinel
      port: 26379
```

- [ ] **Step 4: `k8s/base/redis/service.yaml`** (ClusterIP for app connections)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app.kubernetes.io/name: redis
  ports:
    - name: redis
      port: 6379
      targetPort: 6379
  type: ClusterIP
```

- [ ] **Step 5: Verify Sentinel**
  ```bash
  kubectl -n fla exec redis-0 -c sentinel -- redis-cli -p 26379 SENTINEL masters
  # Expected: fla-master listed with status=ok
  ```

---

## Task 8 — Ingress + TLS (cert-manager)

**Files:**
- Create: `k8s/base/ingress/certificate.yaml`
- Create: `k8s/base/ingress/ingress.yaml`

### Steps

- [ ] **Step 1: Install cert-manager (run once per cluster)**
  ```bash
  kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml
  # Create ClusterIssuer for Let's Encrypt:
  kubectl apply -f - <<EOF
  apiVersion: cert-manager.io/v1
  kind: ClusterIssuer
  metadata:
    name: letsencrypt-prod
  spec:
    acme:
      server: https://acme-v02.api.letsencrypt.org/directory
      email: admin@your-domain.com       # update
      privateKeySecretRef:
        name: letsencrypt-prod-key
      solvers:
        - http01:
            ingress:
              class: nginx
  EOF
  ```

- [ ] **Step 2: `k8s/base/ingress/certificate.yaml`**

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: fla-tls
spec:
  secretName: fla-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - fla.your-domain.com           # update per deployment
```

- [ ] **Step 3: `k8s/base/ingress/ingress.yaml`**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fla
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "500m"    # large log file uploads
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"  # long LLM analysis requests
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    # WebSocket support for agent chat and ingestion progress
    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - fla.your-domain.com
      secretName: fla-tls-secret
  rules:
    - host: fla.your-domain.com
      http:
        paths:
          # API (backend)
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
          # WebSocket endpoints
          - path: /api/v1/ws
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
          # Frontend SPA (catch-all)
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

- [ ] **Step 4: Verify TLS**
  ```bash
  kubectl -n fla get certificate fla-tls
  # Expected: READY=True
  curl -I https://fla.your-domain.com/api/v1/health
  # Expected: HTTP/2 200
  ```

---

## Task 9 — Alembic Migration Job

**Files:**
- Create: `scripts/k8s-migrate.sh`

### Steps

- [ ] **Step 1: Create `scripts/k8s-migrate.sh`**

```bash
#!/usr/bin/env bash
# Run Alembic upgrade head as a Kubernetes Job.
# Usage: ./scripts/k8s-migrate.sh [image_tag]
set -euo pipefail

IMAGE_TAG="${1:-latest}"
JOB_NAME="alembic-migrate-$(date +%s)"

kubectl -n fla apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: fla
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: ghcr.io/org/fla-api:${IMAGE_TAG}
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: fla-api-config
            - secretRef:
                name: fla-api
EOF

echo "Waiting for migration job ${JOB_NAME}..."
kubectl -n fla wait job/"${JOB_NAME}" \
  --for=condition=complete \
  --timeout=120s

echo "Migration logs:"
kubectl -n fla logs job/"${JOB_NAME}"
echo "Migration complete."
```

  ```bash
  chmod +x scripts/k8s-migrate.sh
  ```

---

## Task 10 — Kustomize Overlays

**Files:**
- Create: `k8s/overlays/dev/kustomization.yaml`
- Create: `k8s/overlays/dev/patches/api-replicas.yaml`
- Create: `k8s/overlays/dev/patches/worker-replicas.yaml`
- Create: `k8s/overlays/prod/kustomization.yaml`
- Create: `k8s/overlays/prod/patches/api-resources.yaml`
- Create: `k8s/overlays/prod/patches/worker-llm-resources.yaml`

### Steps

- [ ] **Step 1: `k8s/overlays/dev/kustomization.yaml`**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: fla-dev

resources:
  - ../../base

patches:
  - path: patches/api-replicas.yaml
  - path: patches/worker-replicas.yaml

# Use local registry images in dev
images:
  - name: ghcr.io/org/fla-api
    newName: localhost:5000/fla-api
    newTag: dev
  - name: ghcr.io/org/fla-frontend
    newName: localhost:5000/fla-frontend
    newTag: dev
```

- [ ] **Step 2: `k8s/overlays/dev/patches/api-replicas.yaml`** — single replica, no HPA in dev

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 1
---
# Disable HPA in dev by setting min=max=1
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
spec:
  minReplicas: 1
  maxReplicas: 1
```

- [ ] **Step 3: `k8s/overlays/dev/patches/worker-replicas.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-rule
spec:
  replicas: 1
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-llm
spec:
  replicas: 1
```

- [ ] **Step 4: `k8s/overlays/prod/kustomization.yaml`**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: fla

resources:
  - ../../base

patches:
  - path: patches/api-resources.yaml
  - path: patches/worker-llm-resources.yaml

images:
  - name: ghcr.io/org/fla-api
    newTag: "${IMAGE_TAG}"    # set via CI: kustomize edit set image ...
  - name: ghcr.io/org/fla-frontend
    newTag: "${IMAGE_TAG}"
```

- [ ] **Step 5: `k8s/overlays/prod/patches/api-resources.yaml`** — higher limits for prod

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  template:
    spec:
      containers:
        - name: api
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: "2"
              memory: 2Gi
```

- [ ] **Step 6: `k8s/overlays/prod/patches/worker-llm-resources.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-llm
spec:
  template:
    spec:
      containers:
        - name: worker-llm
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: "2"
              memory: 2Gi
```

- [ ] **Step 7: Validate overlays**
  ```bash
  kubectl kustomize k8s/overlays/dev --dry-run
  kubectl kustomize k8s/overlays/prod --dry-run
  ```
  Expected: renders without error.

---

## Task 11 — Deployment Scripts

**Files:**
- Create: `scripts/k8s-apply.sh`
- Create: `scripts/k8s-rollback.sh`

### Steps

- [ ] **Step 1: `scripts/k8s-apply.sh`** — apply with pre-flight checks

```bash
#!/usr/bin/env bash
# Apply a Kustomize overlay with pre-flight validation.
# Usage: ./scripts/k8s-apply.sh [dev|prod] [image_tag]
set -euo pipefail

OVERLAY="${1:-dev}"
IMAGE_TAG="${2:-latest}"
OVERLAY_DIR="k8s/overlays/${OVERLAY}"

echo "=== Pre-flight checks ==="
kubectl version --client
kubectl cluster-info

echo "=== Setting image tag: ${IMAGE_TAG} ==="
cd "${OVERLAY_DIR}"
kustomize edit set image \
  "ghcr.io/org/fla-api=ghcr.io/org/fla-api:${IMAGE_TAG}" \
  "ghcr.io/org/fla-frontend=ghcr.io/org/fla-frontend:${IMAGE_TAG}"
cd - >/dev/null

echo "=== Dry-run validation ==="
kubectl kustomize "${OVERLAY_DIR}" | kubectl apply --dry-run=server -f -

echo "=== Running migration ==="
./scripts/k8s-migrate.sh "${IMAGE_TAG}"

echo "=== Applying manifests ==="
kubectl kustomize "${OVERLAY_DIR}" | kubectl apply -f -

echo "=== Waiting for rollout ==="
kubectl -n fla rollout status deployment/api --timeout=5m
kubectl -n fla rollout status deployment/worker-rule --timeout=5m
kubectl -n fla rollout status deployment/worker-llm --timeout=5m
kubectl -n fla rollout status deployment/frontend --timeout=5m

echo "=== Post-apply health check ==="
sleep 5
API_IP=$(kubectl -n fla get svc api -o jsonpath='{.spec.clusterIP}')
kubectl -n fla run tmp-health-check --image=curlimages/curl --rm -it --restart=Never -- \
  curl -sf "http://${API_IP}:8000/api/v1/health" | python3 -m json.tool

echo "=== Deploy complete ==="
```

- [ ] **Step 2: `scripts/k8s-rollback.sh`**

```bash
#!/usr/bin/env bash
# Roll back API and worker deployments one revision.
# Usage: ./scripts/k8s-rollback.sh
set -euo pipefail

echo "=== Current rollout history ==="
for deploy in api worker-rule worker-llm frontend; do
  echo "--- ${deploy} ---"
  kubectl -n fla rollout history "deployment/${deploy}"
done

read -rp "Roll back all deployments? [y/N] " confirm
[[ "${confirm}" =~ ^[Yy]$ ]] || exit 0

for deploy in api worker-rule worker-llm frontend; do
  echo "Rolling back deployment/${deploy}..."
  kubectl -n fla rollout undo "deployment/${deploy}"
done

echo "=== Waiting for rollback ==="
for deploy in api worker-rule worker-llm frontend; do
  kubectl -n fla rollout status "deployment/${deploy}" --timeout=3m
done

echo "=== Rollback complete ==="
```

  ```bash
  chmod +x scripts/k8s-apply.sh scripts/k8s-rollback.sh scripts/k8s-migrate.sh
  ```

- [ ] Commit: `git commit -m "feat(k8s): add complete Kubernetes manifests, overlays, and deployment scripts"`

---

## Task 12 — Smoke Test Checklist

Run after `./scripts/k8s-apply.sh dev` on a test cluster:

- [ ] All pods in `fla` namespace reach `Running` state:
  ```bash
  kubectl -n fla get pods
  ```
  Expected: `api-*`, `worker-rule-*`, `worker-llm-*`, `frontend-*`, `postgres-{1,2,3}`, `redis-{0,1,2}` all `Running`.

- [ ] CloudNativePG cluster healthy:
  ```bash
  kubectl -n fla get cluster postgres -o jsonpath='{.status.phase}'
  # Expected: Cluster in healthy state
  ```

- [ ] Redis Sentinel operational:
  ```bash
  kubectl -n fla exec redis-0 -c sentinel -- redis-cli -p 26379 SENTINEL masters
  # Expected: "status" "ok"
  ```

- [ ] API health check passes:
  ```bash
  kubectl -n fla port-forward svc/api 8000:8000 &
  curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
  # Expected: {"status": "ok", "checks": {"db": true, "redis": true}}
  ```

- [ ] Ingress TLS cert issued:
  ```bash
  kubectl -n fla get certificate fla-tls
  # Expected: READY=True
  ```

- [ ] HPA targets registered:
  ```bash
  kubectl -n fla get hpa
  # Expected: all HPAs show TARGETS (not <unknown>)
  ```

- [ ] Migration Job succeeded:
  ```bash
  kubectl -n fla get jobs
  # Expected: alembic-migrate-* COMPLETIONS=1/1
  ```

---

## Handoff Contract

- **Image names:** `ghcr.io/org/fla-api:<tag>` and `ghcr.io/org/fla-frontend:<tag>` — replace `org` with actual GitHub org.
- **Domains:** Update `fla.your-domain.com` in `ingress.yaml` and `certificate.yaml` before first deploy.
- **S3 backup:** Update `destinationPath` in `postgres/cluster.yaml`; create `fla-s3` secret with `ACCESS_KEY_ID` / `SECRET_ACCESS_KEY`.
- **Celery queues:** Rule workers consume `rule` queue; LLM workers consume `llm` queue. Backend code must route tasks to these queues via `@app.task(queue="rule")` / `@app.task(queue="llm")`.
- **WebSocket connections** (agent chat + ingestion progress) require the Ingress `Upgrade` headers — already configured in `ingress.yaml` annotations.
- **Dev overlay** sets `namespace: fla-dev` — keep `fla` for prod to avoid accidental cross-env applies.
- **DB connection string** for the API Deployment is assembled from `fla-postgres` Secret (`username`/`password`) + `fla-api-config` ConfigMap (`DB_HOST`, `DB_PORT`, `DB_NAME`). The `DATABASE_URL` key in the `fla-api` Secret can override this entirely if set.
