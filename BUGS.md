# UDX — Production Readiness Audit

Codebase scanned: `UDX_fullstack/` (React+Vite frontend, FastAPI+MongoDB
backend at `android_app/backend/`, Android Compose client at
`android_app/app/`, integration tests at `tests/`).

Issues are grouped by severity. Each item includes a `file:line`
reference and the recommended fix. Nothing in this list is a style nit
— every entry either breaks in production, leaks data, or blocks a
reproducible deploy.

---

## P0 — Blocks production launch (money loss / data loss / auth bypass)

### 1. Payment gateway is a mock that always succeeds
- **Where:** `android_app/backend/services/payment_service.py:33-38`
  ```python
  async def _gateway_charge_once(card_token: str, amount: float) -> dict:
      if not card_token.startswith("tok_"):
          return {"status": "failed", "transaction_id": ""}
      return {"status": "success", "transaction_id": f"txn_{secrets.token_hex(8)}"}
  ```
- **Impact:** Every `POST /payments/deposit` succeeds without calling any
  real gateway. `wallet_service.credit()` then adds funds to the user's
  balance. If this ships to production, users can top up unlimited money.
- **Fix:** Replace with a real Click/Stripe HTTP call, or make the
  service refuse to start when `ENVIRONMENT=production` and
  `PAYMENT_GATEWAY_URL` is unset.

### 2. `ENVIRONMENT` defaults to `development` → dev router exposed
- **Where:** `android_app/backend/main.py:142-148`
  ```python
  _ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
  if _ENVIRONMENT != "production":
      app.include_router(dev.router)
  ```
- **Impact:** If deployment forgets to set `ENVIRONMENT=production`, the
  whole `/dev/*` surface is public. `POST /dev/reset-seed` in
  `routers/dev.py:49-55` **deletes every User, Category, Product,
  Order, Review, and FraudReport** with no auth. `POST /dev/verify-phone`
  marks any phone as verified without OTP.
- **Fix:** Default to `production`, and require an explicit
  `ENVIRONMENT=development` (or a `DEV_ROUTER_ENABLED=1` flag) to expose
  the dev routes. Also require `Depends(get_current_user)` on every
  `/dev/*` endpoint and check for an admin role.

### 3. `ENCRYPTION_KEY` missing → ephemeral key silently generated
- **Where:** `android_app/backend/core/encryption.py:17-27`
  ```python
  if _enc_hex and len(_enc_hex) == 64:
      _key = bytes.fromhex(_enc_hex)
  else:
      logging.warning("[ENCRYPTION] ENCRYPTION_KEY not set — generating ephemeral key (dev only!)")
      _key = AESGCM.generate_key(bit_length=256)
  ```
- **Impact:** Every restart generates a new AES-GCM key. All previously
  encrypted `phone`, `tin`, `telegram_username` fields in MongoDB become
  permanently undecryptable. Users can no longer log in with their phone.
  `core/security.py:9` correctly raises when `SECRET_KEY` is missing;
  encryption must do the same.
- **Fix:** Raise `RuntimeError` if `ENCRYPTION_KEY` is missing when
  `ENVIRONMENT=production` (or unconditionally).

### 4. `HMAC_KEY` has a default value
- **Where:** `android_app/backend/core/encryption.py:18`
  ```python
  _hmac_secret = os.getenv("HMAC_KEY", "change_this_hmac_secret_in_production").encode()
  ```
- **Impact:** `hmac_hash()` is used as the JWT `sub` claim and as the DB
  index for phone lookups. With the default key, any attacker can
  compute the `phone_hash` for any phone number, forge JWT `sub`
  values, and enumerate users.
- **Fix:** Raise on missing `HMAC_KEY` when
  `ENVIRONMENT=production`.

### 5. Frontend `API_URL` hardcoded, no env override
- **Where:** `src/api.ts:11`
  ```ts
  const API_URL = 'https://udx-marketplace.store';
  ```
- **Impact:** Staging, canary, or local dev builds all hit the
  production API. Every environment change requires a code edit + full
  rebuild. Vite already supports `.env.production` / `.env.staging`.
- **Fix:**
  ```ts
  const API_URL = import.meta.env.VITE_API_URL ?? 'https://udx-marketplace.store';
  ```
  and document `VITE_API_URL` in `.env.example`.

### 6. CORS default allow-list includes dev origins
- **Where:** `android_app/backend/main.py:81`
  ```python
  _raw_origins = os.getenv("ALLOWED_ORIGINS",
      "https://udx-marketplace.store,https://localhost:5173,https://10.0.2.2:8000")
  ```
- **Impact:** If the operator forgets to set `ALLOWED_ORIGINS` in prod,
  the API accepts credentialed requests from `localhost:5173` and
  `10.0.2.2:8000`. Combined with `allow_credentials=True`, that's a
  browser CSRF vector.
- **Fix:** Default to `["https://udx-marketplace.store"]` only; refuse
  to start if `ALLOWED_ORIGINS` includes any localhost origin while
  `ENVIRONMENT=production`.

### 7. Android WebSocket hardcoded to emulator loopback
- **Where:** `android_app/app/src/main/java/com/udx/app/ui/screens/ChatScreen.kt:35`
  ```kotlin
  private const val WS_BASE = "ws://10.0.2.2:8000/ws/chat"
  ```
- **Impact:** WebSocket-based chat can only work in the Android
  emulator against a local uvicorn. On a real device it silently fails.
  Also `ws://` is cleartext.
- **Fix:** Derive from `NetworkModule.BASE_URL` at runtime, replacing
  `https://` with `wss://` and use `wss://udx-marketplace.store/ws/chat`.

### 8. Google OAuth callback interception matches "localhost"
- **Where:** `android_app/app/src/main/java/com/udx/app/ui/screens/GoogleAuthWebViewScreen.kt:74`
  ```kotlin
  if (url.contains("localhost") && url.contains("/auth/google/callback")) {
  ```
- **Impact:** In production the callback returns to
  `udx-marketplace.store`, so this branch is never taken. The WebView
  navigates away and the user never signs in.
- **Fix:** Match on the path only (`Uri.getPath() == "/auth/google/callback"`)
  or match on the production host explicitly.

### 9. Sensitive runtime state committed to the repo
- **Where:**
  - `android_app/backend/verified_sessions.json` — verified-phone hashes
  - `android_app/backend/telegram_chat_ids.json`,
    `telegram_phone_chat_ids.json` — Telegram user → chat_id mappings
  - `android_app/backend/benchmark_results.json`
  - `android_app/backend/uploads/` — 17 user-uploaded images
  - `android_app/bugreport-sdk_gphone16k_arm64-*.zip` — 6.9 MB
    Android bug report
- **Impact:** Sensitive user identifiers are checked in, and every
  deploy overwrites live state on the next server restart if the volume
  isn't persistent.
- **Fix:** Add all of the above to `.gitignore`, remove from the tree,
  and move to a runtime volume (or Redis for the JSONs — the code
  already has a Redis path).

### 10. Duplicate frontend copies in `Icon/`
- **Where:** `Icon/UDX/`, `Icon/UDX (1)/`, `Icon/UDX (2)/`
- **Impact:** Three full copies of the frontend source tree, ~20 MB
  each. Confuses grep, ide search, and CI checkouts.
- **Fix:** Delete `Icon/` entirely (it's not referenced by any build
  target).

---

## P1 — Should be fixed before public traffic

### 11. Documentation is stale / wrong
- **Where:** `RUN_PROJECT.md`
- Says backend lives at `backend/main.py`; it's actually at
  `android_app/backend/main.py`.
- Uses Windows PowerShell + `C:\Users\user\Downloads\UDX (2) 2\UDX (2)`
  paths.
- Recommends SQLite; the real code uses **MongoDB** + `beanie`.
- Recommends `python -m uvicorn backend.main:app`, but the module uses
  `import models` / `import database` (bare imports), so the CWD must
  be `android_app/backend/` and the command is
  `python -m uvicorn main:app`.
- Says frontend runs on port 5173; `vite.config.ts:21` sets
  `port: 3000, open: true`.
- **Fix:** Rewrite for Linux+production, drop SQLite mentions, correct
  the module path and port, cover the actual `.env` matrix (Mongo,
  Redis, R2, Sentry, Click, Telegram, Neo4j, Google OAuth).

### 12. `passlib` deprecated + unused
- **Where:** `android_app/backend/requirements.txt:6`
- `core/security.py` uses `import bcrypt` directly; passlib is dead
  weight. Passlib itself is unmaintained.
- **Fix:** Remove `passlib[bcrypt]`.

### 13. All Radix UI deps pinned to `"*"`
- **Where:** `package.json:6-31`
- Every `npm install` can pull a different version — irreproducible
  builds.
- **Fix:** Pin ranges (`^1.2.0` etc.) and commit `package-lock.json`
  (already present — but with `"*"` the lock file is meaningless once
  someone runs `npm install --package-lock-only`).

### 14. React 18 runtime + React 19 types
- **Where:** `package.json:41-55`
  ```
  "react": "^18.3.1"
  "@types/react": "^19.2.13"
  "@types/react-dom": "^19.2.3"
  ```
- Type checker will report API mismatches on hooks / event handlers
  removed in React 19. Compile may succeed but behavior drifts.
- **Fix:** Match types to runtime — either upgrade both to 19 or pin
  types to `^18.3`.

### 15. ReDoS via user-controlled regex on product search
- **Where:** `android_app/backend/routers/products.py:135-138`
  ```python
  if q and q.strip():
      import re
      regex = re.compile(q.strip(), re.IGNORECASE)
      query = query.find({"name": {"$regex": regex.pattern, "$options": "i"}})
  ```
- **Impact:** User controls the regex source. A crafted pattern like
  `(a+)+$` on the server + `$regex` on MongoDB → both sides can be
  DoS'd.
- **Fix:** `re.escape(q.strip())` before feeding it into the regex.

### 16. `datetime.utcnow()` deprecated in Python 3.12+
- **Where:** `core/security.py:23,25`, `routers/chat.py:107,112,158,168,215,222`,
  `routers/contracts.py` (via schemas), `routers/click_payment.py:182,234,270`
- Silent `DeprecationWarning` today, hard removal soon.
- **Fix:** `datetime.now(timezone.utc)` everywhere.

### 17. Google OAuth CSRF nonce store is process-local when Redis is down
- **Where:** `android_app/backend/routers/auth.py:290-297` (`_csrf_issue`)
  and the corresponding verification path.
- **Impact:** On multi-worker deploys (uvicorn `--workers 4`, gunicorn),
  the nonce issued by worker A may be verified by worker B → 100% CSRF
  failure. On single worker a crash loses all pending nonces.
- **Fix:** Require Redis in production; refuse to start if
  `ENVIRONMENT=production` and `REDIS_URL` is unset.

### 18. Same multi-worker issue for OTP, pending tokens, verified sessions,
Telegram chat IDs
- **Where:**
  - `routers/auth.py:34-36` (`_otp_store`, `_phone_otp_store`, `_pending_tokens`)
  - `telegram_bot.py:49,52` (`_username_to_chat_id`, `_phone_hash_to_chat_id`
    — loaded from disk on boot, written on every OTP)
- **Impact:** OTP set by worker A can't be verified by worker B. Under
  concurrent writes the JSON files race and one write clobbers the
  other (`json.dump` is not atomic).
- **Fix:** Redis-only in production. If the JSON fallback stays,
  wrap in a lock + atomic write (`os.replace` after writing a temp
  file).

### 19. `verify_password(None)` will crash for OAuth users
- **Where:** `android_app/backend/routers/auth.py:258`
  ```python
  if not user or not verify_password(form_data.password, user.hashed_password):
  ```
- **Impact:** Google OAuth users have `hashed_password = None`. Calling
  `bcrypt.checkpw(pw, None.encode())` raises `AttributeError` → uvicorn
  returns a raw 500 which leaks a stack trace and doesn't log via the
  audit path.
- **Fix:**
  ```python
  if not user or not user.hashed_password or not verify_password(...):
  ```

### 20. `add_price_history` allows anyone to rewrite a product's price
- **Where:** `android_app/backend/routers/products.py:58-71`
- **Impact:** Endpoint is not gated by `Depends(get_current_user)` and
  does not verify `product.seller_id == current_user.id`. Any anonymous
  caller can `POST /products/{id}/prices/` and overwrite `product.price`
  (line 68).
- **Fix:** Require auth + seller ownership check.

### 21. `orders.py` has no idempotency key
- **Where:** `android_app/backend/routers/orders.py:12-48`
- **Impact:** A network retry double-creates an order. The payments
  path (`services/payment_service.py`) already models idempotency
  correctly; orders don't.
- **Fix:** Same `X-Idempotency-Key` pattern as
  `wallet_service.credit(idempotency_key=...)`.

### 22. Rate limiter uses raw remote address, no XFF trust list
- **Where:** `android_app/backend/core/rate_limiter.py:21`
  ```python
  limiter = Limiter(key_func=get_remote_address)
  ```
- **Impact:** Behind Nginx / Cloudflare every request appears to come
  from `127.0.0.1` → one attacker exhausts the shared bucket. The
  `X-Forwarded-For` header is also blindly copied into audit logs
  (`services/payment_service.py:95`) without validating it against a
  trusted proxy list.
- **Fix:** Use `slowapi.util.get_ipaddr` with an explicit trust list
  (`TRUSTED_PROXIES` env var) and validate `X-Forwarded-For` before
  logging.

### 23. Weather API key placed in URL query string
- **Where:** `android_app/backend/routers/weather.py:15`
- **Impact:** `?appid=<key>` shows up in access logs (uvicorn, nginx,
  Cloudflare) and in the OpenWeather side. Rotating the key requires
  purging all those logs.
- **Fix:** Move to header if the provider supports it, or minimally
  scrub the query string when logging.

### 24. OTP token entropy is only ~30 bits
- **Where:** `android_app/backend/routers/auth.py:182`
  ```python
  token = str(uuid.uuid4())[:8].upper()
  ```
- **Impact:** 8 hex chars = 2^32 space; brute-forceable in seconds if
  an attacker knows the endpoint.
- **Fix:** `secrets.token_urlsafe(16)`.

---

## P2 — Hardening + hygiene before scale

### 25. Chat WebSocket auth token in the query string
- **Where:** `android_app/backend/routers/chat.py:174-189`
- Query strings end up in access logs. Prefer
  `Sec-WebSocket-Protocol` or a short-lived signed nonce.

### 26. `chat.send_message` has no length cap
- **Where:** `routers/chat.py:90-119` (HTTP path). The WS handler caps
  at 4000 bytes (`chat.py:208`); the HTTP path has no cap.
- **Fix:** Enforce `len(message_text) <= 4000` server-side.

### 27. Android JWT stored in plain `SharedPreferences`
- **Where:** `android_app/app/src/main/java/com/udx/app/data/TokenManager.kt`
- On rooted devices or via adb backup, the token leaks.
- **Fix:** `EncryptedSharedPreferences` with the Android Keystore.

### 28. `AndroidManifest.xml` — `allowBackup="true"`
- **Where:** `android_app/app/src/main/AndroidManifest.xml:8`
- adb backup can extract the app's private storage including the JWT.
- **Fix:** `android:allowBackup="false"` for release builds (or a strict
  `android:fullBackupContent` rule that excludes `auth_prefs`).

### 29. OkHttp logs full bodies (including bearer tokens) in every build
- **Where:** `android_app/app/src/main/java/com/udx/app/data/NetworkModule.kt:25`
  ```kotlin
  level = HttpLoggingInterceptor.Level.BODY
  ```
- **Fix:** Gate on `BuildConfig.DEBUG` (`if (BuildConfig.DEBUG) BODY else NONE`).

### 30. `google-services.json` committed to repo
- **Where:** `android_app/app/google-services.json`
- Firebase API keys are safe to expose in mobile builds (they're
  client identifiers, not secrets), but the file should be provided
  per-environment (dev/stg/prod). Committing production credentials
  means dev builds hit prod Firebase.
- **Fix:** `.gitignore` and inject in CI (`app/src/{debug,release}/google-services.json`).

### 31. `network_security_config.xml` allows cleartext for `localhost`
+ `10.0.2.2`
- **Where:** `android_app/app/src/main/res/xml/network_security_config.xml`
- Only affects those two domains, but the file itself is a dev-only
  concession. Ship a separate release-only config with the whole
  `<domain-config>` block removed.

### 32. `magic bytes` allow-list doesn't cover HEIC / AVIF
- **Where:** `android_app/backend/routers/products.py:23-38`
- iOS photos are HEIC by default. Upload silently rejected with
  `INVALID_IMAGE_TYPE`.
- **Fix:** Add `image/heic`, `image/heif`, `image/avif` (with matching
  magic bytes) or transcode server-side.

### 33. `requirements.txt` is unpinned
- **Where:** `android_app/backend/requirements.txt`
- Only `motor<4.0.0` has an upper bound. Everything else is `>=`.
- **Fix:** `pip-compile` a `requirements.lock` and use it in CI.

### 34. `Neo4j` driver commented out
- **Where:** `android_app/backend/requirements.txt:20`
  ```
  # neo4j>=5.0.0
  ```
- The code at `core/neo4j_db.py:18` imports `neo4j.GraphDatabase`. If
  someone follows README instructions and Neo4j isn't installed, the
  ML recommendations silently degrade (which is by design — but not
  obvious).
- **Fix:** Either uncomment (and document that it's optional at
  runtime via `NEO4J_URI`) or split into `requirements-ml.txt`.

### 35. `/uploads` mount falls back to local when R2 misconfigured
- **Where:** `main.py:76-78`
- Behavior: if any single R2 env var is missing, R2 is treated as
  "not configured" and the app silently switches to local disk. In
  production this masks a config error and starts serving user
  uploads from the container's ephemeral filesystem.
- **Fix:** Require all R2 vars in production; hard-fail if partial.

### 36. `_normalize_phone` doesn't cover common formats
- **Where:** `routers/auth.py:240-245`
- Only `isdigit()` triggers the leading `+`. A phone `"+998 (90)
  1234567"` becomes `"+998(90)1234567"` and never matches on later
  logins if the same user re-registers with a different formatting.
- **Fix:** Strip everything but digits and `+`, then prepend `+` if
  missing.

### 37. Frontend swallows API errors as `console.error`
- **Where:** `src/App.tsx:65-72, 96-108`
- `try { ... } catch (error) { console.error(...) }` never surfaces
  a toast to the user. Users think the app is fine while product
  data silently falls back to mock.
- **Fix:** `toast.error(t('errors.load_products'))` on failure.

### 38. Frontend order history is hardcoded mock data
- **Where:** `src/App.tsx:112-134` (`orderHistory` initial state).
- Shows fake orders on every load until the user creates one.
- **Fix:** `useEffect(() => api.getOrders(token).then(setOrderHistory))`.

### 39. `SettingsScreen` fetches `api.frankfurter.app` directly
- **Where:** `src/components/SettingsScreen.tsx:58`
- Third-party CORS-open API called from the browser. If the API goes
  down (or removes CORS), the settings screen breaks.
- **Fix:** Proxy through the backend + cache in Redis.

### 40. `services/payment_service.py:95` blindly trusts `X-Forwarded-For`
- IP-based audit logs are meaningless if the header is forgeable.
- **Fix:** Only accept the header when the request came from a
  trusted proxy (per issue #22).

### 41. `services/audit_service.py` insertion path has no
back-pressure — any spike in traffic hammers Mongo. Consider batching
via the existing `services/event_bus.py`.

### 42. `print()` calls in production code
- `database.py:17,25,55`, `routers/auth.py:238`, `routers/chat.py:227`,
  `routers/products.py:202` — should all be `logger.info/error/warning`
  so they honor the log level, JSON formatter, and Sentry breadcrumbs.

### 43. `logging.basicConfig(level=logging.INFO)` at module import
- **Where:** `main.py:11`
- Overridden unpredictably by uvicorn / gunicorn / Sentry. Move to
  `if __name__ == "__main__":` or use `logging.config.dictConfig()`.

### 44. `authlib` in requirements but never imported
- **Where:** `android_app/backend/requirements.txt:7`
- Google OAuth in `routers/auth.py` uses `httpx` + raw endpoints. Drop
  the dep.

### 45. Vite dev server config `open: true` in `vite.config.ts:22`
- Harmless for local, but reads oddly in a repo that ships to prod.
  Remove or move behind `mode === "development"`.

### 46. No health-check gating for start-up dependencies
- **Where:** `main.py:52-66` (`lifespan`) — DB failure raises, but
  Redis/Telegram bot/R2 failures are silently swallowed inside their
  own init routines. A container that "starts" but has no Redis
  passes k8s liveness checks and silently rate-limits nothing.
- **Fix:** `/health` already reports per-service status; also expose
  `/readyz` that returns 503 until all critical deps are up.

### 47. `payments.py:38` card-type detection uses first-digit table
- Misses Diners (300–305, 3095, 36, 38–39), JCB (3528–3589),
  UnionPay (62), Maestro (50, 56–58, 6…). Non-security, but the
  `card_type` shown to the user is wrong for common cards.

### 48. No CI, no linter, no type-check gate
- **Where:** `package.json:60-63` scripts block has only `dev` and
  `build`. No `lint`, `typecheck`, `test`.
- **Fix:** Add `"typecheck": "tsc --noEmit"`, `"lint": "eslint src"`,
  `"test": "vitest"`, and wire them into a CI workflow.

---

## Suggested remediation order

1. **Same-day (P0):** #1 (payment mock), #2 (ENV default), #3 (encryption
   key), #4 (HMAC key), #6 (CORS default), #9 (secrets in repo).
2. **Before public beta (P0 remainder + P1):** #5, #7, #8, #10, plus
   #11 (docs), #17 (Redis required), #19 (auth crash), #20 (price
   history auth).
3. **Before scale-out:** the rest of P1 + the Android hardening block
   (#27–#31).
4. **Ongoing:** P2 hygiene.

---

## Not audited in this pass

- `models.py` / `schemas.py` — Pydantic + Beanie models
- `routers/reviews.py`, `routers/click_payment.py` full logic
- `core/ml_recommendations.py` — SVD pipeline
- `services/event_bus.py`, `services/event_handlers.py`
- All React components under `src/components/**`
- Test fixtures under `tests/backend/*` beyond `conftest.py` / `test_api.py`
- Kotlin ViewModels + repository layer beyond `NetworkModule.kt`,
  `TokenManager.kt`, `ChatScreen.kt`, `GoogleAuthWebViewScreen.kt`
- Neo4j Cypher queries in `routers/dev.py::ml_stats`

A second pass on those would surface more findings, but the items
above are the ones that will bite you the moment real traffic hits
`https://udx-marketplace.store`.
