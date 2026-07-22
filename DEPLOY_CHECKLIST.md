# UDX — Deploy oldidan to'ldirilishi kerak bo'lgan qismlar

Bu fayl faqat "nimani, qayerda, nima bilan to'ldirish kerak" ro'yxati.
Ishga tushirish buyruqlari uchun [`RUN_PROJECT.md`](RUN_PROJECT.md) §6 ga
qarang. Hozirgi deploy yo'li — Docker Compose (`docker-compose.yml`).
AWS/ECS yo'li (`infra/`, `AWS_DEPLOY.md`) hozircha eskirgan va
ishlatilmaydi.

---

## 1. `.env.docker` — asosiy fayl

Manba: [`.env.docker.example`](.env.docker.example)

```sh
cp .env.docker.example .env.docker
```

So'ng `.env.docker` faylida quyidagilarni to'ldiring:

### 1.1 MAJBURIY — bularsiz `docker compose up` boshlanmaydi

| O'zgaruvchi | Qayerda ishlatiladi | Qanday olish/generatsiya qilish |
| --- | --- | --- |
| `SECRET_KEY` | JWT imzolash (`backend/main.py`) | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ENCRYPTION_KEY` | `backend/core/encryption.py` — telefon/TIN/telegram username shifrlash | `python3 -c "import secrets; print(secrets.token_hex(32))"` (64 hex belgi) |
| `HMAC_KEY` | `backend/core/security.py` | 32+ belgili tasodifiy satr |
| `POSTGRES_PASSWORD` | `postgres` konteyneri + backend `DATABASE_URL` | O'zingiz belgilaysiz, kuchli parol |
| `REDIS_PASSWORD` | `redis` konteyneri + backend `REDIS_URL` | O'zingiz belgilaysiz, kuchli parol |
| `ALLOWED_ORIGINS` | CORS (`backend/main.py`) | Frontend domeningiz, masalan `https://udx-marketplace.store` — `localhost` bo'lmasin, aks holda backend ishga tushmaydi (`ENVIRONMENT=production` bo'lganda) |

### 1.2 SHART EMAS, lekin funksiya ishlashi uchun kerak

| O'zgaruvchi | Qaysi funksiyani yoqadi | Qayerdan olish |
| --- | --- | --- |
| `PAYMENT_GATEWAY_URL` | Karta orqali to'lov (`backend/services/payment_service.py`) — bo'sh bo'lsa va `PAYMENT_ALLOW_MOCK` ham o'rnatilmagan bo'lsa, `ENVIRONMENT=production`da to'lovlar rad etiladi | Haqiqiy to'lov gateway provayderingizdan |
| `PAYMENT_ALLOW_MOCK` | Faqat staging/smoke-test uchun `=1` — production trafikda **HECH QACHON** yoqmang | — |
| `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY`, `CLICK_MERCHANT_USER_ID`, `CLICK_RETURN_URL` | Click to'lov integratsiyasi (`backend/routers/click_payment.py`) | Click.uz merchant kabinetidan |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google orqali kirish/ro'yxatdan o'tish | Google Cloud Console → batafsil: [`backend/GOOGLE_OAUTH_SETUP.md`](backend/GOOGLE_OAUTH_SETUP.md) |
| `TELEGRAM_BOT_TOKEN` | OTP kodlarni Telegram orqali yuborish (`backend/telegram_bot.py`) | @BotFather orqali bot yarating |
| `OPENWEATHER_API_KEY` | Ob-havo vidjeti (`backend/routers/weather.py`) | https://openweathermap.org/api (bepul) |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` | Cloudflare R2 fayl xotirasi (`backend/core/storage.py`) — hammasi to'ldirilmasa, backend lokal `/uploads/` papkasiga tushadi | Cloudflare dashboard → R2 |
| `SENTRY_DSN` | Xatolarni kuzatish | https://sentry.io loyihangiz sozlamalaridan |
| `DEV_ADMIN_TOKEN` | Faqat `ENVIRONMENT=production` bo'lmaganda ishlatiladi — production'da kerak emas | — |

### 1.3 Odatiy qiymatlari yetarli (o'zgartirish shart emas)

`GATEWAY_RATE`, `GATEWAY_BURST`, `GATEWAY_CB_*`, `FRONTEND_HTTP_PORT`,
`VITE_API_URL`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` —
`.env.docker.example`dagi standart qiymatlar kichik marketplace uchun
yetarli.

---

## 2. Frontend build-vaqti konfiguratsiyasi

Manba: [`.env.example`](.env.example) (repo ildizida)

Docker Compose yo'lida bu avtomatik — `.env.docker`dagi `VITE_API_URL`
`frontend` build argumentiga uzatiladi (`docker-compose.yml`, `frontend`
xizmati, `build.args.VITE_API_URL`). Alohida `npm run build` qilsangiz:

```sh
cp .env.example .env.production
# VITE_API_URL qiymatini tekshiring/tahrirlang
```

---

## 3. Android ilova (ixtiyoriy — faqat mobil client chiqarilsa)

### 3.1 Backend manzili

Fayl: `android_app/app/src/main/java/com/udx/app/data/NetworkModule.kt:16`

```kotlin
const val BASE_URL = "https://udx-marketplace.store/"
```

Agar backend domeningiz boshqacha bo'lsa, shu qatorni to'g'ridan-to'g'ri
tahrirlang (yoki build variant orqali override qiling).

### 3.2 Imzolash kalitlari (release build uchun)

`android_app/app/build.gradle.kts:26-28` quyidagi environment
o'zgaruvchilarini o'qiydi — build oldidan export qiling:

```sh
export KEYSTORE_PATH=/absolute/path/to/udx-release.jks
export KEYSTORE_PASSWORD=***
export KEY_ALIAS=udx
export KEY_PASSWORD=***
export VERSION_CODE=<keyingi raqam>
export VERSION_NAME=<masalan 1.0.1>
```

`.jks` keystore fayli hali yo'q bo'lsa, yarating:

```sh
keytool -genkey -v -keystore udx-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias udx
```

**Bu faylni hech qachon git'ga qo'shmang** — `.gitignore`da
`android_app/app/keystore/` allaqachon istisno qilingan.

### 3.3 Google Services (agar push-notification/Firebase ishlatilsa)

`android_app/app/google-services.json` — Firebase konsolidan yuklab
oling, `android_app/app/` papkasiga qo'ying. `.gitignore`da istisno
qilingan, git'ga tushmaydi.

---

## 4. Tekshirish ketma-ketligi

1. `.env.docker` to'ldirilgach: `docker compose --env-file .env.docker config` — xato bo'lsa (`variable is not set`), qaysi qiymat yetishmayotganini ko'rsatadi.
2. `docker compose --env-file .env.docker up -d` — barcha health-check'lar `healthy` bo'lguncha kuting (`docker compose ps`).
3. `curl http://localhost:${FRONTEND_HTTP_PORT:-8080}/api/health` — backend va uning bog'liqliklari (`postgres`, `redis`, `storage`) holatini ko'rsatishi kerak.
4. To'lov: agar `PAYMENT_GATEWAY_URL` bo'sh va `PAYMENT_ALLOW_MOCK` ham o'rnatilmagan bo'lsa, `/payments/deposit` **qasddan** rad etadi — bu kutilgan xatti-harakat, xato emas.

---

## 5. Hozircha to'ldirilmaydigan qism

`infra/` (AWS ECS/CloudFront) va `AWS_DEPLOY.md` — eski MongoDB/Neo4j
arxitekturasiga mo'ljallangan va hozirgi Postgres+memdb+gateway+logagg
stackga mos emas. AWS'ga chiqarish rejalashtirilsa, bu qism alohida
qayta loyihalanishi kerak.
