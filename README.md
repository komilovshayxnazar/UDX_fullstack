# UDX

UDX is a full-stack B2C/B2B marketplace: buyers and sellers trade
products through a web app and an Android client, with contracts,
in-app chat, reviews, fraud reporting, and both card and Click
(Uzbekistan) payment flows built in. This repo is a monorepo — web
frontend, backend API, Android app, and three supporting Go services
all live here and ship together via one `docker compose` stack.

## Architecture

| Layer          | Path                 | Runtime                                   |
| -------------- | -------------------- | ------------------------------------------ |
| Web frontend   | `src/`                | Vite + React 18 + TypeScript, Radix UI     |
| Backend API    | `backend/`            | FastAPI + Motor (MongoDB), Beanie ODM      |
| Android client | `android_app/`        | Kotlin + Jetpack Compose                   |
| Rate-limit gateway | `services/dyn-gateway/` | Go — reverse proxy, token-bucket limiter, circuit breaker |
| Log aggregator | `services/logagg/`    | Go — gRPC ingest, WAL, chunk store, query CLI |
| In-memory store | `services/memdb/`     | Go — KV store + WAL, backend's OTP/session store |

Supporting infra (all run via Docker): **MongoDB** (primary DB),
**Redis** (cache + OTP/session fallback), **Neo4j** (optional,
recommendation graph), **Nginx** (serves the built frontend, fronts
the API).

### Request path

```
Browser ──▶ Nginx ──▶ /api/*  ──▶ gateway (rate limit + circuit breaker) ──▶ backend (FastAPI)
                  └──▶ /ws/*, /uploads/*  ─────────────────────────────▶ backend (direct)

backend ──▶ MongoDB (data)
        ├─▶ memdb (OTP/session, primary) ──▶ Redis (fallback) ──▶ in-process (last resort)
        ├─▶ Redis (product/category cache)
        ├─▶ Neo4j (recommendations, optional)
        └─▶ JSON-line log file ──▶ logagg-agent ──▶ logagg-server (searchable log store)
```

## Features

- **Marketplace core** — products, categories, price history, orders,
  B2B/B2C pricing, seller profiles, buyer/seller-specific UI.
- **Contracts** between buyers and sellers, with status tracking.
- **In-app chat** over WebSockets, plus reviews and fraud reporting.
- **Payments** — card payments and the Click gateway (Uzbekistan),
  idempotency keys, wallet + transaction ledger, audit log.
- **Auth** — phone/Telegram-bot OTP login and Google OAuth, JWT
  sessions.
- **Recommendations** — SVD-based, backed by an optional Neo4j graph.
- **Weather** widget via OpenWeather.
- **Localization** — Android app ships English, Russian, and five
  Central Asian locales (uz, kk, ky, tg + more).
- **Observability** — Sentry error tracking, structured JSON-line
  logs shipped to an in-house log aggregator, `/health` endpoint
  covering every backing service.
- **Resilience** — edge rate limiting and a load-adaptive circuit
  breaker in front of the API, a durable WAL-backed store for
  session-critical data.

## Repo layout

```
src/               Web frontend (Vite + React + TS)
backend/           FastAPI backend (Motor/Beanie, routers, services, core)
android_app/       Android client (Kotlin + Jetpack Compose)
services/
  dyn-gateway/     Rate-limit / circuit-breaker reverse proxy (Go)
  logagg/          Distributed log aggregator: agent + server + query CLI (Go)
  memdb/           In-memory KV store with WAL (Go) + Python client
docker/            Nginx config for the frontend container
docker-compose.yml Full stack: mongo, redis, neo4j, memdb, backend,
                   gateway, logagg-server, logagg-agent, frontend
infra/             AWS deployment artefacts (see AWS_DEPLOY.md)
```

## Quick start

The whole stack, in one command:

```sh
cp .env.docker.example .env.docker    # fill in the required secrets
docker compose --env-file .env.docker up -d
```

This builds and starts every service above and serves the app at
`http://localhost:${FRONTEND_HTTP_PORT:-8080}`. See
[`RUN_PROJECT.md`](RUN_PROJECT.md) for the manual, non-Docker setup
(useful for iterating on one layer at a time) and prerequisites.

## More docs

- [`RUN_PROJECT.md`](RUN_PROJECT.md) — full run/deploy guide, manual setup per layer
- [`AWS_DEPLOY.md`](AWS_DEPLOY.md) — production deployment on AWS
- [`NEO4J_SETUP.md`](NEO4J_SETUP.md) — enabling the recommendation graph
- [`BUGS.md`](BUGS.md) — production-readiness audit log
- `backend/*.md` — Google OAuth, messaging API, password rules, weather API setup
- `services/*/README.md` — each Go service's design and CLI flags
