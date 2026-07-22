# UDX — Run & Deploy

The stack:

| Layer          | Path                          | Runtime                    |
| -------------- | ----------------------------- | -------------------------- |
| Frontend       | `src/`                        | Vite + React 18 + TS       |
| Backend        | `backend/`        | FastAPI + SQLAlchemy 2.0 (async) + asyncpg |
| Android client | `android_app/app/`            | Jetpack Compose            |
| Primary DB     | PostgreSQL 16 (schema owned by Alembic) | |
| Cache / OTP    | Redis (optional in dev)       |                            |
| Durable OTP/session store | `services/memdb/` (Go, WAL-backed) | |
| Object store   | Cloudflare R2 (falls back to local `uploads/`) |         |

**TL;DR — the whole stack in one command:**

```sh
cp .env.docker.example .env.docker    # fill in the required secrets
docker compose --env-file .env.docker up -d
```

That brings up PostgreSQL, Redis, memdb, the FastAPI backend, the Go
gateway, the log aggregator (server + agent), and an Nginx container
serving the built frontend + reverse-proxying `/api/*` (through the
gateway) and `/ws/*` to the backend. See §6 for details. The
manual-install path (§§1–4) is retained for local development without
Docker.

---

## Prerequisites

- Node 18+ / npm 10+
- Python 3.11+
- PostgreSQL 16 running locally or a connection URI
- Redis (optional in dev; **required in production** — session/OTP/CSRF state
  spans workers)
- Docker + Docker Compose v2 (recommended for the whole-stack path)

---

## 1. Backend

### 1.1 Environment

The backend imports its neighboring modules by bare name
(`import models`, `import db`), so run it with `backend/`
as the working directory. Create `backend/.env` from
`.env.example`:

```env
# Required in production
ENVIRONMENT=production            # dev: leave as "development"
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<64 hex chars, e.g. python -c "import secrets; print(secrets.token_hex(32))">
HMAC_KEY=<32+ char random string>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/udx
ALLOWED_ORIGINS=https://udx-marketplace.store
REDIS_URL=redis://redis:6379/0

# Optional (feature-toggled)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://udx-marketplace.store/auth/google/callback
OPENWEATHER_API_KEY=...
TELEGRAM_BOT_TOKEN=...
CLICK_SERVICE_ID=...
CLICK_MERCHANT_ID=...
CLICK_SECRET_KEY=...
CLICK_MERCHANT_USER_ID=...
CLICK_RETURN_URL=https://udx-marketplace.store/wallet
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=udx-media
R2_PUBLIC_URL=https://media.udx.uz
SENTRY_DSN=https://xxx@ooo.ingest.sentry.io/zzz
PAYMENT_GATEWAY_URL=https://gateway.example.com
DEV_ADMIN_TOKEN=<random, only if ENVIRONMENT!=production>
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Fail-closed behavior when `ENVIRONMENT=production`:

- `SECRET_KEY`, `ENCRYPTION_KEY`, `HMAC_KEY` must be set — startup raises.
- `ALLOWED_ORIGINS` must not contain `localhost` / `10.0.2.2` / `127.0.0.1`.
- Payment routes refuse to charge unless `PAYMENT_GATEWAY_URL` is set
  (or `PAYMENT_ALLOW_MOCK=1` is set explicitly for a staging smoke).
- `/dev/*` router is not mounted at all.
- Google OAuth env is required if any Google auth endpoint is used.

### 1.2 Install & run (local dev)

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# One-shot Postgres + Redis for dev
docker run -d --name udx-postgres -e POSTGRES_USER=udx -e POSTGRES_PASSWORD=udx -e POSTGRES_DB=udx -p 5432:5432 postgres:16-alpine
docker run -d --name udx-redis -p 6379:6379 redis:7

# Apply migrations before first run (and after any model change)
DATABASE_URL=postgresql+asyncpg://udx:udx@localhost:5432/udx alembic upgrade head

ENVIRONMENT=development \
  SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  HMAC_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  DATABASE_URL=postgresql+asyncpg://udx:udx@localhost:5432/udx \
  REDIS_URL=redis://localhost:6379/0 \
  python -m uvicorn main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>
Health: <http://localhost:8000/health>

### 1.3 Production (systemd or containers)

```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

Front with Nginx / Caddy / Traefik and terminate TLS there. Put Redis in
front of anything OTP-related — the in-memory fallback does not span
workers and will silently break login / OAuth CSRF at any concurrency
above `--workers 1`.

---

## 2. Frontend

### 2.1 Install & run

```sh
cd <repo-root>
cp .env.example .env.local     # then edit VITE_API_URL if needed
npm install
npm run dev    # http://localhost:3000 (from vite.config.ts)
```

`src/api.ts` reads `VITE_API_URL` (defaulting to
`https://udx-marketplace.store` if unset). Set one of `.env`,
`.env.production`, `.env.staging`, or `.env.local` before `npm run build`
so a build for staging doesn't hit prod.

### 2.2 Build

```sh
VITE_API_URL=https://staging.udx-marketplace.store npm run build
# output: build/
```

Serve the `build/` directory with any static host. On a single-page-app
host (Cloudflare Pages, Netlify, Vercel), make sure to add a fallback
rewrite of `/* → /index.html` so React Router deep links work.

---

## 3. Android client

```sh
cd android_app
./gradlew :app:assembleRelease
```

Environment for signing:

```sh
export KEYSTORE_PATH=/absolute/path/to/udx-release.jks
export KEYSTORE_PASSWORD=***
export KEY_ALIAS=udx
export KEY_PASSWORD=***
export VERSION_CODE=2
export VERSION_NAME=1.0.1
```

`app/src/main/res/xml/network_security_config.xml` still allows cleartext
for `localhost` + `10.0.2.2` (Android emulator loopback) so the debug
build can talk to a local backend. It affects only those two domains, so
production traffic still uses TLS.

If you point the app at a non-production backend, override
`NetworkModule.BASE_URL` in a build variant instead of editing the
constant — the WebSocket URL derives from it automatically.

---

## 4. Tests

```sh
cd tests/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
API_URL=http://localhost:8000 pytest -v
```

Backend integration tests hit the running server — start `main.py` first.

---

## 5. Common failure modes

| Symptom                                               | Fix                                             |
| ----------------------------------------------------- | ----------------------------------------------- |
| `SECRET_KEY environment variable is not set.`         | Set `SECRET_KEY` in `backend/.env`  |
| `ENCRYPTION_KEY is required when ENVIRONMENT=production` | Generate + set `ENCRYPTION_KEY`              |
| `HMAC_KEY is required when ENVIRONMENT=production`    | Generate + set `HMAC_KEY`                       |
| `ALLOWED_ORIGINS contains dev origins in production`  | Remove `localhost` from `ALLOWED_ORIGINS`       |
| `Refusing to charge — mock gateway in production`     | Set `PAYMENT_GATEWAY_URL` or (staging) `PAYMENT_ALLOW_MOCK=1` |
| Chat / OTP works for one user but breaks on scale-up  | Deploy Redis, set `REDIS_URL`                   |
| Android chat won't connect                            | Ensure the server is reachable at `wss://<host>/ws/chat` and TLS cert is valid |
| `POSTGRES_PASSWORD is required` (compose)             | Copy `.env.docker.example` → `.env.docker` and fill in required values |

---

## 6. Docker Compose (whole stack)

`docker-compose.yml` defines eight services on one bridge network:

| Service         | Image / build              | Exposed to host      |
| ---------------- | -------------------------- | -------------------- |
| `postgres`       | `postgres:16-alpine`       | (internal only)      |
| `redis`          | `redis:7-alpine`           | (internal only)      |
| `memdb`          | build from `services/memdb`| (internal only)      |
| `backend`        | build from `backend/`      | (internal only, port 8000) |
| `gateway`        | build from `services/dyn-gateway` | (internal only, port 8080) |
| `logagg-server`  | build from `services/logagg` (`Dockerfile.server`) | (internal only) |
| `logagg-agent`   | build from `services/logagg` (`Dockerfile.agent`) | (internal only) |
| `frontend`       | build from repo root       | `${FRONTEND_HTTP_PORT:-8080}:80` |

Only the frontend publishes a host port. The browser hits Nginx, which
serves the built Vite bundle and reverse-proxies

- `/api/*`      → `gateway:8080/*` (rate-limited + circuit-broken, forwards to `backend:8000`)
- `/ws/*`       → `backend:8000/ws/*` (WebSocket upgrade preserved, bypasses the gateway)
- `/uploads/*`  → `backend:8000/uploads/*` (only used if R2 is not configured)

so the browser only ever talks to one origin — same-origin API kills
the whole CORS-in-prod class of bugs. `logagg-agent` tails the
backend's JSON-line log file (via the shared `backend-logs` volume)
and streams it to `logagg-server` for indexing/search.

### 6.1 Bootstrap

```sh
cp .env.docker.example .env.docker

# Generate the three cryptographic keys (backend fails to start without them).
python3 -c "import secrets; print('SECRET_KEY='     + secrets.token_hex(32))" >> .env.docker
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(32))" >> .env.docker
python3 -c "import secrets; print('HMAC_KEY='       + secrets.token_hex(32))" >> .env.docker

# Fill in POSTGRES_PASSWORD, REDIS_PASSWORD, and any optional
# integrations (Click, Google OAuth, Telegram, R2, Sentry, …).
$EDITOR .env.docker

docker compose --env-file .env.docker up -d
```

### 6.2 Day-to-day

```sh
docker compose --env-file .env.docker logs -f backend
docker compose --env-file .env.docker restart backend
docker compose --env-file .env.docker down                 # keep volumes
docker compose --env-file .env.docker down -v              # WIPE volumes
```

### 6.3 Building only what changed

Compose rebuilds on `up --build` only if the corresponding build
context changed:

```sh
docker compose --env-file .env.docker up -d --build backend
docker compose --env-file .env.docker up -d --build frontend
```

### 6.4 Data volumes

| Volume            | Purpose                                          |
| ----------------- | ------------------------------------------------ |
| `postgres-data`   | PostgreSQL data directory                        |
| `redis-data`      | Redis AOF/RDB                                    |
| `memdb-data`      | memdb's WAL + snapshots                          |
| `logagg-data`     | logagg-server's chunk store + index              |
| `backend-uploads` | Local `/app/uploads` (only used without R2)      |
| `backend-state`   | `/app/state` for the OTP/Telegram JSON fallback  |
| `backend-logs`    | JSON-line app log, shared with `logagg-agent`    |

They persist across `docker compose down` unless you pass `-v`.

### 6.5 What Docker Compose does NOT ship

- The **Android app** — build it with `./gradlew :app:assembleRelease` per §3.
- The **Telegram bot polling loop** — it runs inside the `backend`
  container as a startup task; make sure `TELEGRAM_BOT_TOKEN` is set
  before `up` if you need OTP delivery.
- **TLS termination** — production should sit behind an ingress (nginx
  on the host, Traefik, or a managed ALB) that handles HTTPS. The
  container Nginx listens on plain HTTP by design.
