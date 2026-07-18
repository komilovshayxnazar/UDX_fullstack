from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
import logging
import httpx
import secrets
from datetime import timedelta
import os
import time
import json

logger = logging.getLogger(__name__)

import models
import schemas
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from core.encryption import encrypt, decrypt, hmac_hash
from core.errors import E
from core.cache import get_redis
from core.memdb_store import is_memdb_enabled, memdb_get, memdb_set, memdb_delete
from core.rate_limiter import limiter
from services.audit_service import log as audit_log
from telegram_bot import (
    send_otp, get_chat_id,
    send_otp_to_chat, send_otp_by_phone_hash,
    get_chat_id_by_token, get_chat_id_by_phone_hash,
    set_token_callback,
)

OTP_TTL_SECONDS    = 300   # 5 daqiqa
OTP_MAX_ATTEMPTS   = 5
VERIFIED_TTL_SECONDS = 600  # 10 daqiqa

BOT_USERNAME = "udxregister_bot"

# ── In-memory fallback (Redis yo'q bo'lganda ishlatiladi) ────────────────────
_otp_store:        dict[str, tuple[str, float, int]] = {}
_phone_otp_store:  dict[str, tuple[str, float, int]] = {}
_pending_tokens:   dict[str, tuple[str, str, float]] = {}

VERIFIED_SESSIONS_FILE = "verified_sessions.json"

def _load_verified_store() -> dict[str, float]:
    try:
        with open(VERIFIED_SESSIONS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_verified_store(store: dict[str, float]) -> None:
    with open(VERIFIED_SESSIONS_FILE, "w") as f:
        json.dump(store, f)

# ── OTP / session / token helpers ─────────────────────────────────────────────
#
# Storage tiers, tried in order: memdb (durable — WAL survives a restart) ->
# Redis (fast, TTL-native, lost on restart if AOF/RDB is off) -> in-process
# dict / file (single-instance last resort). memdb has no native TTL, so its
# JSON payloads carry an "exp" unix timestamp checked on read, matching the
# style already used by the in-process fallback below.

async def _otp_set(ns: str, key: str, code: str, attempts: int = 0) -> None:
    rkey = f"udx:otp:{ns}:{key}"
    if is_memdb_enabled():
        payload = json.dumps({"code": code, "attempts": attempts,
                              "exp": time.time() + OTP_TTL_SECONDS}).encode()
        if await memdb_set(rkey, payload):
            return
    r = get_redis()
    if r:
        await r.setex(rkey, OTP_TTL_SECONDS,
                      json.dumps({"code": code, "attempts": attempts}))
    else:
        store = _otp_store if ns == "tg" else _phone_otp_store
        store[key] = (code, time.time() + OTP_TTL_SECONDS, attempts)

async def _otp_get(ns: str, key: str) -> dict | None:
    rkey = f"udx:otp:{ns}:{key}"
    if is_memdb_enabled():
        raw = await memdb_get(rkey)
        if raw is not None:
            data = json.loads(raw)
            if time.time() < data["exp"]:
                return {"code": data["code"], "attempts": data["attempts"]}
            await memdb_delete(rkey)
            return None
    r = get_redis()
    if r:
        raw = await r.get(rkey)
        return json.loads(raw) if raw else None
    store = _otp_store if ns == "tg" else _phone_otp_store
    entry = store.get(key)
    if entry and time.time() < entry[1]:
        return {"code": entry[0], "attempts": entry[2]}
    return None

async def _otp_incr(ns: str, key: str) -> None:
    rkey = f"udx:otp:{ns}:{key}"
    if is_memdb_enabled():
        raw = await memdb_get(rkey)
        if raw is not None:
            data = json.loads(raw)
            data["attempts"] += 1
            await memdb_set(rkey, json.dumps(data).encode())
            return
    r = get_redis()
    if r:
        raw = await r.get(rkey)
        if raw:
            data = json.loads(raw)
            data["attempts"] += 1
            ttl = await r.ttl(rkey)
            await r.setex(rkey, max(ttl, 1), json.dumps(data))
    else:
        store = _otp_store if ns == "tg" else _phone_otp_store
        if key in store:
            c, exp, att = store[key]
            store[key] = (c, exp, att + 1)

async def _otp_del(ns: str, key: str) -> None:
    rkey = f"udx:otp:{ns}:{key}"
    if is_memdb_enabled():
        await memdb_delete(rkey)
    r = get_redis()
    if r:
        await r.delete(rkey)
    store = _otp_store if ns == "tg" else _phone_otp_store
    store.pop(key, None)

async def _token_set(token: str, phone_hash: str, otp_code: str) -> None:
    rkey = f"udx:token:{token}"
    if is_memdb_enabled():
        payload = json.dumps({"phone_hash": phone_hash, "otp_code": otp_code,
                              "exp": time.time() + OTP_TTL_SECONDS}).encode()
        if await memdb_set(rkey, payload):
            return
    r = get_redis()
    if r:
        await r.setex(rkey, OTP_TTL_SECONDS,
                      json.dumps({"phone_hash": phone_hash, "otp_code": otp_code}))
    else:
        _pending_tokens[token] = (phone_hash, otp_code, time.time() + OTP_TTL_SECONDS)

async def _token_get(token: str) -> tuple | None:
    rkey = f"udx:token:{token}"
    if is_memdb_enabled():
        raw = await memdb_get(rkey)
        if raw is not None:
            d = json.loads(raw)
            if time.time() < d["exp"]:
                return d["phone_hash"], d["otp_code"], 0
            await memdb_delete(rkey)
            return None
    r = get_redis()
    if r:
        raw = await r.get(rkey)
        if not raw:
            return None
        d = json.loads(raw)
        return d["phone_hash"], d["otp_code"], 0
    entry = _pending_tokens.get(token)
    return entry if (entry and time.time() < entry[2]) else None

async def _token_del(token: str) -> None:
    rkey = f"udx:token:{token}"
    if is_memdb_enabled():
        await memdb_delete(rkey)
    r = get_redis()
    if r:
        await r.delete(rkey)
    _pending_tokens.pop(token, None)

# ── Session helpers ──────────────────────────────────────────────────────────

async def _session_set(key: str) -> None:
    rkey = f"udx:session:{key}"
    if is_memdb_enabled():
        payload = json.dumps({"exp": time.time() + VERIFIED_TTL_SECONDS}).encode()
        if await memdb_set(rkey, payload):
            return
    r = get_redis()
    if r:
        await r.setex(rkey, VERIFIED_TTL_SECONDS, "1")
    else:
        store = _load_verified_store()
        store[key] = time.time() + VERIFIED_TTL_SECONDS
        _save_verified_store(store)

async def consume_verified_session(username: str) -> bool:
    """True qaytaradi va sessiyani o'chiradi (bir martalik)."""
    username = username.lower().lstrip("@")
    rkey = f"udx:session:{username}"
    if is_memdb_enabled():
        raw = await memdb_get(rkey)
        if raw is not None:
            await memdb_delete(rkey)
            data = json.loads(raw)
            return time.time() < data["exp"]
    r = get_redis()
    if r:
        val = await r.get(rkey)
        if val:
            await r.delete(rkey)
            return True
        return False
    # Fayl fallback
    store = _load_verified_store()
    exp = store.get(username)
    if exp and time.time() < exp:
        store.pop(username)
        _save_verified_store(store)
        return True
    if username in store:
        store.pop(username)
        _save_verified_store(store)
    return False

router = APIRouter(tags=["auth"])

async def _on_token_arrived(token: str, chat_id: int) -> None:
    """Bot tokenni qabul qilganda OTP ni yuboradi."""
    entry = await _token_get(token)
    if not entry:
        return
    phone_hash, otp_code, _ = entry
    sent = await send_otp_to_chat(chat_id, otp_code)
    if sent:
        await _otp_set("phone", phone_hash, otp_code)
        await _token_del(token)

set_token_callback(_on_token_arrived)


@router.post("/auth/otp/init-phone")
async def init_phone_otp(body: schemas.PhoneOtpInit):
    """
    Telefon raqami asosida OTP jarayonini boshlaydi.
    Token va bot_username qaytaradi — app deep link ochadi.
    """
    phone = _normalize_phone(body.phone)
    phone_hash = hmac_hash(phone)

    # ~128 bits of entropy; a truncated UUID (~30 bits) is brute-forceable
    # in seconds. urlsafe(16) → 22 char base64url string.
    token = secrets.token_urlsafe(16)
    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = time.time() + OTP_TTL_SECONDS

    # Agar foydalanuvchi botda telefon ulashgan bo'lsa — darhol OTP yuborish
    if await get_chat_id_by_phone_hash(phone_hash):
        sent = await send_otp_by_phone_hash(phone_hash, otp_code)
        if sent:
            await _otp_set("phone", phone_hash, otp_code)
            return {
                "token": None,
                "bot_username": BOT_USERNAME,
                "expires_in": OTP_TTL_SECONDS,
                "direct": True,
            }

    # Aks holda — token orqali deeplink flow
    await _token_set(token, phone_hash, otp_code)
    return {
        "token": token,
        "bot_username": BOT_USERNAME,
        "expires_in": OTP_TTL_SECONDS,
        "direct": False,
    }


@router.post("/auth/otp/verify-phone")
async def verify_phone_otp(body: schemas.PhoneOtpVerify):
    """Telefon va OTP kodni tasdiqlaydi."""
    phone = _normalize_phone(body.phone)
    phone_hash = hmac_hash(phone)

    entry = await _otp_get("phone", phone_hash)
    if not entry:
        raise HTTPException(status_code=400, detail=E.OTP_NOT_FOUND)

    if entry["attempts"] >= OTP_MAX_ATTEMPTS:
        await _otp_del("phone", phone_hash)
        raise HTTPException(status_code=429, detail=E.OTP_TOO_MANY_ATTEMPTS)

    if body.code != entry["code"]:
        await _otp_incr("phone", phone_hash)
        raise HTTPException(status_code=400, detail=E.OTP_INVALID)

    await _otp_del("phone", phone_hash)
    await _session_set(phone_hash)
    return {"detail": "OTP tasdiqlandi."}


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

_IS_PROD = os.getenv("ENVIRONMENT", "production").lower() == "production"
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
    # Warn (or fail-closed in production) so other auth routes still work
    # in dev; a real Google-OAuth call will 500 naturally if used.
    msg = "Google OAuth environment variables are not fully configured."
    if _IS_PROD:
        raise RuntimeError(f"[CONFIG] {msg}")
    logger.warning("[CONFIG] %s", msg)

def _normalize_phone(raw: str) -> str:
    """Strip spaces/dashes, ensure leading + for digit-only strings."""
    phone = raw.strip().replace(" ", "").replace("-", "")
    if phone.isdigit():
        phone = "+" + phone
    return phone


@router.post("/token", response_model=schemas.Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    phone = _normalize_phone(form_data.username)
    ph    = hmac_hash(phone)
    user  = await models.User.find_one(models.User.phone_hash == ph)

    # OAuth-registered users have no `hashed_password`; guard against
    # calling bcrypt.checkpw on None to avoid a raw 500 + stack trace.
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        # Muvaffaqiyatsiz login — audit log (user topilgan bo'lsa)
        if user:
            await audit_log(
                user=user,
                action=models.AuditAction.login_failed,
                detail={"reason": "wrong_password"},
                request=request,
                success=False,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=E.INCORRECT_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": ph},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    await audit_log(
        user=user,
        action=models.AuditAction.login,
        detail={},
        request=request,
        success=True,
    )
    return {"access_token": access_token, "token_type": "bearer"}

_CSRF_TTL = 600  # 10 daqiqa


async def _csrf_issue(action: str) -> str:
    """CSRF nonce yaratadi va Redis/memory'da saqlaydi."""
    nonce = secrets.token_urlsafe(32)
    r = get_redis()
    if r:
        await r.setex(f"udx:oauth_csrf:{nonce}", _CSRF_TTL, action)
    else:
        _csrf_store[nonce] = (action, time.time() + _CSRF_TTL)
    return nonce


async def _csrf_consume(nonce: str) -> str | None:
    """Nonce ni tekshiradi va o'chiradi. Action qaytaradi yoki None."""
    r = get_redis()
    if r:
        rkey = f"udx:oauth_csrf:{nonce}"
        action = await r.get(rkey)
        if action:
            await r.delete(rkey)
            return action
        return None
    entry = _csrf_store.pop(nonce, None)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


_csrf_store: dict[str, tuple[str, float]] = {}


@router.get("/auth/google/register")
async def google_register():
    nonce = await _csrf_issue("register")
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"state=register:{nonce}"
    )
    return {"auth_url": google_auth_url}

@router.get("/auth/google/login")
async def google_login():
    nonce = await _csrf_issue("login")
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"state=login:{nonce}"
    )
    return {"auth_url": google_auth_url}

@router.get("/auth/google/callback")
async def google_callback(code: str, state: str = None):
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail=E.GOOGLE_TOKEN_FAILED)

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(userinfo_url, headers=headers)

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail=E.GOOGLE_USERINFO_FAILED)
        
        user_info = userinfo_response.json()
    
    email = user_info.get("email")
    google_id = user_info.get("id")
    name = user_info.get("name")

    # CSRF state tekshiruvi: "action:nonce" formatida kelishi kerak
    action = None
    if state and ":" in state:
        raw_action, nonce = state.split(":", 1)
        action = await _csrf_consume(nonce)
        if action != raw_action:
            raise HTTPException(status_code=400, detail="errors.oauth_invalid_state")
    elif state in ("register", "login"):
        # Eski client'lar uchun (CSRF yo'q) — production'da o'chirish kerak
        action = state
    else:
        raise HTTPException(status_code=400, detail="errors.oauth_invalid_state")

    user = await models.User.find_one(models.User.phone_hash == hmac_hash(f"google_{google_id}"))

    if action == "register":
        if user:
            return {"error": "already_registered"}

        raw_phone = f"google_{google_id}"
        ph = hmac_hash(raw_phone)
        user = models.User(
            phone=encrypt(raw_phone),
            phone_hash=ph,
            hashed_password=None,
            role=models.UserRole.buyer,
            name=name or email,
            avatar=user_info.get("picture")
        )
        await user.insert()

        app_access_token = create_access_token(
            data={"sub": ph},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"token": app_access_token, "registered": True}

    else:  # action == "login"
        if not user:
            return {"error": "not_registered"}

        app_access_token = create_access_token(
            data={"sub": user.phone_hash},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"token": app_access_token, "registered": False}


@router.post("/auth/otp/request")
async def request_telegram_otp(body: schemas.TelegramOtpRequest):
    """
    Generate a 6-digit OTP and send it to the user via Telegram.
    The user must have already sent /start to the UDX bot.
    """
    username = body.telegram_username.lower().lstrip("@")
    username_h = hmac_hash(username)

    if not await get_chat_id(username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=E.TELEGRAM_USER_NOT_FOUND,
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    await _otp_set("tg", username, code)

    sent = await send_otp(username, code)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=E.TELEGRAM_OTP_FAILED,
        )

    return {"detail": "OTP sent to your Telegram."}


@router.post("/auth/otp/verify")
async def verify_telegram_otp(body: schemas.TelegramOtpVerify):
    """Verify the OTP code the user received on Telegram."""
    username = body.telegram_username.lower().lstrip("@")

    entry = await _otp_get("tg", username)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.OTP_NOT_FOUND)

    if entry["attempts"] >= OTP_MAX_ATTEMPTS:
        await _otp_del("tg", username)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=E.OTP_TOO_MANY_ATTEMPTS)

    if body.code != entry["code"]:
        await _otp_incr("tg", username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.OTP_INVALID)

    await _otp_del("tg", username)
    await _session_set(username)
    return {"detail": "OTP verified successfully."}
