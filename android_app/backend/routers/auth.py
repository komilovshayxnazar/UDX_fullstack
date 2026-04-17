from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from datetime import timedelta
import os
import uuid
import random
import time
import json

import models
import schemas
from core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from core.encryption import encrypt, decrypt, hmac_hash
from core.errors import E
from core.cache import get_redis
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

# ── Redis OTP helpers ────────────────────────────────────────────────────────

async def _otp_set(ns: str, key: str, code: str, attempts: int = 0) -> None:
    r = get_redis()
    if r:
        await r.setex(f"udx:otp:{ns}:{key}", OTP_TTL_SECONDS,
                      json.dumps({"code": code, "attempts": attempts}))
    else:
        store = _otp_store if ns == "tg" else _phone_otp_store
        store[key] = (code, time.time() + OTP_TTL_SECONDS, attempts)

async def _otp_get(ns: str, key: str) -> dict | None:
    r = get_redis()
    if r:
        raw = await r.get(f"udx:otp:{ns}:{key}")
        return json.loads(raw) if raw else None
    store = _otp_store if ns == "tg" else _phone_otp_store
    entry = store.get(key)
    if entry and time.time() < entry[1]:
        return {"code": entry[0], "attempts": entry[2]}
    return None

async def _otp_incr(ns: str, key: str) -> None:
    r = get_redis()
    rkey = f"udx:otp:{ns}:{key}"
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
    r = get_redis()
    if r:
        await r.delete(f"udx:otp:{ns}:{key}")
    else:
        store = _otp_store if ns == "tg" else _phone_otp_store
        store.pop(key, None)

async def _token_set(token: str, phone_hash: str, otp_code: str) -> None:
    r = get_redis()
    if r:
        await r.setex(f"udx:token:{token}", OTP_TTL_SECONDS,
                      json.dumps({"phone_hash": phone_hash, "otp_code": otp_code}))
    else:
        _pending_tokens[token] = (phone_hash, otp_code, time.time() + OTP_TTL_SECONDS)

async def _token_get(token: str) -> tuple | None:
    r = get_redis()
    if r:
        raw = await r.get(f"udx:token:{token}")
        if not raw:
            return None
        d = json.loads(raw)
        return d["phone_hash"], d["otp_code"], 0
    entry = _pending_tokens.get(token)
    return entry if (entry and time.time() < entry[2]) else None

async def _token_del(token: str) -> None:
    r = get_redis()
    if r:
        await r.delete(f"udx:token:{token}")
    else:
        _pending_tokens.pop(token, None)

# ── Session helpers ──────────────────────────────────────────────────────────

async def _session_set(key: str) -> None:
    r = get_redis()
    if r:
        await r.setex(f"udx:session:{key}", VERIFIED_TTL_SECONDS, "1")
    else:
        store = _load_verified_store()
        store[key] = time.time() + VERIFIED_TTL_SECONDS
        _save_verified_store(store)

async def consume_verified_session(username: str) -> bool:
    """True qaytaradi va sessiyani o'chiradi (bir martalik)."""
    username = username.lower().lstrip("@")
    r = get_redis()
    if r:
        rkey = f"udx:session:{username}"
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

    token = str(uuid.uuid4())[:8].upper()
    otp_code = str(random.randint(100000, 999999))
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

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
    # We will print a warning instead of crashing immediately so other auth routes still work,
    # but any attempt to use Google login will fail naturally or we could raise an error during the request.
    print("WARNING: Google OAuth environment variables are not fully configured.")

def _normalize_phone(raw: str) -> str:
    """Strip spaces/dashes, ensure leading + for digit-only strings."""
    phone = raw.strip().replace(" ", "").replace("-", "")
    if phone.isdigit():
        phone = "+" + phone
    return phone


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    phone = _normalize_phone(form_data.username)
    ph    = hmac_hash(phone)
    user  = await models.User.find_one(models.User.phone_hash == ph)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=E.INCORRECT_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": ph},   # JWT sub = phone_hash
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/google/register")
async def google_register():
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"state=register"
    )
    return {"auth_url": google_auth_url}

@router.get("/auth/google/login")
async def google_login():
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"state=login"
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
    
    user = await models.User.find_one(models.User.phone_hash == hmac_hash(f"google_{google_id}"))
    
    if state == "register":
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

    else:
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

    code = str(random.randint(100000, 999999))
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
