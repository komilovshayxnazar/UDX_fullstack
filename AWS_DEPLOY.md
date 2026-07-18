# UDX on AWS

Production deployment recipe. This file complements `RUN_PROJECT.md`
(local dev) and `docker-compose.yml` (dev-parity boot). Skim the
architecture, then follow the numbered steps.

## Architecture

```
                                Route 53
                                    │
              ┌─────────────────────┴─────────────────────┐
              ▼                                           ▼
     https://udx-marketplace.store             https://api.udx-marketplace.store
              │                                           │
       CloudFront (SPA)                            ALB (HTTPS, ACM cert)
              │                                           │
       S3 bucket (build/)                     ECS Fargate service (udx-backend)
                                                          │
                             ┌──────────────┬────────────┼────────────┬──────────────┐
                             ▼              ▼            ▼            ▼              ▼
                         DocumentDB    ElastiCache  RDS Postgres  Neo4j EC2      S3 (media)
                         (MongoDB)     (Redis)      (optional)    or Aura         via R2 or
                                                                                 native S3
```

| Component  | AWS service                          | Notes                                             |
| ---------- | ------------------------------------ | ------------------------------------------------- |
| React TS   | **S3 + CloudFront**                  | Static bundle. Origin Access Control + SPA fallback. |
| FastAPI    | **ECS Fargate** behind an ALB        | Alt: App Runner (simpler, but no VPC endpoints). |
| MongoDB    | **DocumentDB** (or MongoDB Atlas)    | Works with the Motor driver over TLS.            |
| PostgreSQL | **RDS PostgreSQL**                   | Not currently used by the code — see §7.        |
| Neo4j      | **EC2 + Docker** or **Neo4j Aura DB**| **Do not use Neptune** — see §Neptune warning.   |
| Redis      | **ElastiCache** (Redis 7)            | Required in prod (session/OTP/CSRF).             |
| Media      | **S3** (public via CloudFront) or R2 | Set `R2_*` env vars (or write a small S3 shim).  |
| Secrets    | **AWS Secrets Manager**              | Injected via ECS task definition `secrets:`.     |
| Logs       | **CloudWatch Logs**                  | stdout → awslogs driver.                          |
| Metrics    | **CloudWatch** + Sentry              | Sentry DSN via secret.                            |

### Neptune warning

The recommender in `backend/core/neo4j_db.py` uses Cypher over the Bolt
driver. Neptune supports **openCypher** over an HTTPS endpoint signed
with SigV4, not the Bolt protocol. Neither the driver nor the queries
carry over cleanly. Options:

- **Recommended:** run Neo4j Community on EC2 (single node) or use
  **Neo4j AuraDB** (managed cloud).
- If you must use Neptune, rewrite the Cypher queries in
  `neo4j_db.py` against `boto3.client('neptunedata')` — non-trivial.

---

## 1 · One-time bootstrap

### 1.1 Route 53 + ACM

Register (or import) `udx-marketplace.store`. In us-east-1 (required
for CloudFront) request an ACM certificate for
`udx-marketplace.store` + `www.udx-marketplace.store`. In your primary
region (e.g. `eu-central-1`) request another ACM cert for
`api.udx-marketplace.store` for the ALB.

### 1.2 VPC

Use the default VPC or create a small one with:

- 2× public subnets (ALB, NAT)
- 2× private subnets (ECS tasks, DocumentDB, ElastiCache, RDS)

Security groups:

| SG name       | Ingress                                  |
| ------------- | ---------------------------------------- |
| `sg-alb`      | 443/tcp from 0.0.0.0/0                   |
| `sg-backend`  | 8000/tcp from `sg-alb`                   |
| `sg-docdb`    | 27017/tcp from `sg-backend`              |
| `sg-redis`    | 6379/tcp from `sg-backend`               |
| `sg-neo4j`    | 7687/tcp from `sg-backend`               |
| `sg-rds`      | 5432/tcp from `sg-backend`               |

### 1.3 ECR repository

```sh
aws ecr create-repository \
  --repository-name udx-backend \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

### 1.4 S3 buckets

```sh
aws s3api create-bucket --bucket udx-frontend-prod --region us-east-1
aws s3api create-bucket --bucket udx-media-prod    --region us-east-1
```

Attach the policy in `infra/s3-cloudfront-bucket-policy.json` (edit the
distribution ID + account ID first) to the frontend bucket.

### 1.5 CloudFront

- Origin: `udx-frontend-prod.s3.us-east-1.amazonaws.com`
- Origin access: **OAC** (Origin Access Control)
- Default root object: `index.html`
- Custom error responses:
  - `403 → /index.html`, TTL 0 (SPA fallback)
  - `404 → /index.html`, TTL 0
- Behaviors:
  - Default: cache everything, forward no headers.
  - `/index.html`: `Cache-Control: no-cache` (short TTL).
- Alternate domain: `udx-marketplace.store` (attach the us-east-1 ACM
  cert).

### 1.6 ECS cluster + task role

```sh
aws ecs create-cluster --cluster-name udx-prod
```

Create two IAM roles:

- `udx-ecs-task-execution-role` — attach `AmazonECSTaskExecutionRolePolicy`
  plus a policy that grants `secretsmanager:GetSecretValue` on the
  secrets used below.
- `udx-ecs-task-role` — permissions the app needs at runtime (S3 media
  bucket, CloudWatch Logs, Sentry outbound).

### 1.7 Secrets Manager

Create one secret per sensitive env var (or a single JSON secret with
all keys). Names used by `infra/ecs-task-definition.template.json`:

```
udx/prod/SECRET_KEY
udx/prod/ENCRYPTION_KEY
udx/prod/HMAC_KEY
udx/prod/MONGODB_URL
udx/prod/REDIS_URL
udx/prod/NEO4J_URI
udx/prod/NEO4J_USER
udx/prod/NEO4J_PASSWORD
udx/prod/GOOGLE_CLIENT_ID
udx/prod/GOOGLE_CLIENT_SECRET
udx/prod/OPENWEATHER_API_KEY
udx/prod/TELEGRAM_BOT_TOKEN
udx/prod/CLICK_SECRET_KEY
udx/prod/SENTRY_DSN
udx/prod/DEV_ADMIN_TOKEN
```

### 1.8 DocumentDB / ElastiCache / RDS / Neo4j

- DocumentDB cluster, `engine-version=5.0.0`, TLS enabled. Use the
  AWS-provided CA in the connection URI:
  `mongodb://...?tls=true&tlsCAFile=/etc/ssl/certs/rds-combined-ca-bundle.pem`
- ElastiCache Redis 7, cluster mode disabled, one replica for HA.
- RDS PostgreSQL only if you add Postgres (§7).
- Neo4j: launch a `t3.medium` in a private subnet running the official
  Docker image, mount `/data` on EBS, expose 7687 only inside the VPC.

Store each connection URI as a Secrets Manager secret.

---

## 2 · Frontend deploy — S3 + CloudFront

Wired up by `.github/workflows/deploy-frontend.yml`. Trigger:

- Push to `main` that touches `src/**`, `package.json`, `vite.config.ts`,
  or `Dockerfile` (root).
- Manual `workflow_dispatch`.

The workflow:

1. `npm ci && VITE_API_URL=https://api.udx-marketplace.store npm run build`
2. `aws s3 sync build/ s3://udx-frontend-prod/ --delete --cache-control 'public, max-age=31536000, immutable'`
3. Re-upload `index.html` with `Cache-Control: no-cache, no-store, must-revalidate`
4. `aws cloudfront create-invalidation --paths '/*'`

Required GitHub secrets:

```
AWS_ROLE_TO_ASSUME_FRONTEND
AWS_REGION
FRONTEND_S3_BUCKET       (e.g. udx-frontend-prod)
CLOUDFRONT_DISTRIBUTION  (e.g. E123ABC...)
VITE_API_URL             (e.g. https://api.udx-marketplace.store)
```

Uses OIDC (`aws-actions/configure-aws-credentials`) — no long-lived
IAM keys in GitHub.

---

## 3 · Backend deploy — ECR + ECS

Wired up by `.github/workflows/deploy-backend.yml`. Trigger:

- Push to `main` that touches `backend/**`.
- Manual `workflow_dispatch`.

Steps:

1. Build multi-arch image (`linux/amd64`) from `backend/Dockerfile`.
2. Tag with the short commit SHA + `latest`.
3. `docker push` to
   `${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/udx-backend`.
4. Render `infra/ecs-task-definition.template.json` → new revision.
5. `aws ecs update-service --force-new-deployment` and wait for the
   service to stabilise.

Required GitHub secrets:

```
AWS_ROLE_TO_ASSUME_BACKEND
AWS_REGION
ECR_REPOSITORY           (e.g. udx-backend)
ECS_CLUSTER              (e.g. udx-prod)
ECS_SERVICE              (e.g. udx-backend)
ECS_TASK_DEFINITION      (family name, e.g. udx-backend)
TASK_EXECUTION_ROLE_ARN
TASK_ROLE_ARN
```

---

## 4 · ALB + target group

- Target group `udx-backend-tg`, protocol HTTP, port 8000, target
  type `ip` (Fargate).
- Health check: `GET /health`, healthy threshold 2, unhealthy 3,
  interval 15s, timeout 5s.
- ALB listener 443 → forward to `udx-backend-tg`.
- Listener 80 → 301 redirect to 443.
- ALB HTTPS listener attached to the `api.udx-marketplace.store` ACM
  cert (regional).

Set `ALLOWED_ORIGINS=https://udx-marketplace.store` on the ECS task —
this matches the CloudFront domain the browser uses.

---

## 5 · Frontend/backend origin split

CloudFront serves the SPA from `https://udx-marketplace.store`. The
browser calls the API at `https://api.udx-marketplace.store`. Two
choices:

- **CORS (default in this repo):** frontend was built with
  `VITE_API_URL=https://api.udx-marketplace.store`. Backend's CORS
  allow-list is `https://udx-marketplace.store`. This is what the
  workflow assumes.

- **Same-origin via CloudFront path routing:** add a CloudFront
  behavior `/api/*` and `/ws/*` with the ALB as origin. Then set
  `VITE_API_URL=/api`. Best for latency + no CORS at all, but ALB
  origins in CloudFront need an origin request policy that forwards
  all headers.

---

## 6 · Observability

- CloudWatch Logs group `/ecs/udx-backend`, retention 30 days
  (configured by the task definition).
- Container Insights on the ECS cluster.
- Sentry DSN via `udx/prod/SENTRY_DSN`.
- `/health` on the ALB returns per-service status (`mongodb`, `redis`,
  `storage`).

---

## 7 · PostgreSQL (RDS) — future work

The current code is Mongo-only via Beanie. RDS PostgreSQL is listed in
the deployment target, so before pointing anything at it:

1. Decide which entities move to Postgres (e.g. `Order`, `Transaction`,
   `Contract`, `AuditLog` — anything relational-heavy).
2. Add `sqlalchemy[asyncio]` + `asyncpg` + `alembic` to
   `backend/requirements.txt`.
3. Add `backend/core/postgres.py` with an async engine + session
   factory.
4. Migrate the chosen models from Beanie `Document` to SQLAlchemy
   `Mapped` classes, write Alembic migrations, and update the routers.

Until then, provision RDS but leave `DATABASE_URL` unset — nothing in
the code will read it.

---

## 8 · Local dev-parity

Everything above assumes production credentials. For local development
against real AWS resources you can still use `docker compose` — set the
same env vars in `.env.docker` and comment out the `mongo`, `redis`,
`neo4j` services in `docker-compose.yml` so the backend talks to the
remote endpoints.

---

## 9 · Rollback

- **Backend:** `aws ecs update-service --task-definition udx-backend:<N-1>`
  reverts the service to the previous revision.
- **Frontend:** the S3 bucket has versioning on (see
  `infra/s3-cloudfront-bucket-policy.json`); re-upload the previous
  `build/` from a tagged git commit, then invalidate CloudFront again.
