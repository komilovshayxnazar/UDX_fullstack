# UDX — Run & Deploy

The stack:

| Layer          | Path                          | Runtime                    |
| -------------- | ----------------------------- | -------------------------- |
| Frontend       | `src/`                        | Vite + React 18 + TS       |
| Backend        | `backend/`        | FastAPI + Motor (MongoDB)  |
| Android client | `android_app/app/`            | Jetpack Compose            |
| Cache / OTP    | Redis (optional in dev)       |                            |
| Object store   | Cloudflare R2 (falls back to local `uploads/`) |         |
| Graph DB       | Neo4j (optional for recs)     |                            |

The old README instructions (SQLite, PowerShell paths under
`C:\Users\user\Downloads\UDX (2) 2`) are stale. Follow the steps below.

---

## Prerequisites

- Node 18+ / npm 10+
- Python 3.11+
- MongoDB 6+ running locally or a connection URI
- Redis (optional in dev; **required in production** — session/OTP/CSRF state
  spans workers)
- Docker (optional — quick Mongo + Redis)

---

## 1. Backend

### 1.1 Environment

The backend imports its neighboring modules by bare name
(`import models`, `import database`), so run it with `backend/`
as the working directory. Create `backend/.env` from
`.env.example`:

```env
# Required in production
ENVIRONMENT=production            # dev: leave as "development"
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<64 hex chars, e.g. python -c "import secrets; print(secrets.token_hex(32))">
HMAC_KEY=<32+ char random string>
MONGODB_URL=mongodb://user:pass@host:27017/udx
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
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<strong-random>
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

# One-shot Mongo + Redis for dev
docker run -d --name udx-mongo -p 27017:27017 mongo:7
docker run -d --name udx-redis -p 6379:6379 redis:7

ENVIRONMENT=development \
  SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  HMAC_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  MONGODB_URL=mongodb://localhost:27017/udx \
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
