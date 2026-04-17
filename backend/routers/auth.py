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
from telegram_bot import (
    send_otp, get_chat_id,
    send_otp_to_chat, send_otp_by_phone_hash,
    get_chat_id_by_token, get_chat_id_by_phone_hash,
    set_token_callback,
)

# In-memory OTP store: { telegram_username -> (code, expires_at, attempts) }
_otp_store: dict[str, tuple[str, float, int]] = {}
# Phone-based OTP store: { phone_hash -> (code, expires_at, attempts) }
_phone_otp_store: dict[str, tuple[str, float, int]] = {}
# Pending tokens: { token -> (phone_hash, otp_code, expires_at) }
_pending_tokens: dict[str, tuple[str, str, float]] = {}
OTP_TTL_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 5

BOT_USERNAME = "udxregister_bot"

VERIFIED_SESSIONS_FILE = "verified_sessions.json"
VERIFIED_TTL_SECONDS = 600  # 10 minutes to complete registration


def _load_verified_store() -> dict[str, float]:
    try:
        with open(VERIFIED_SESSIONS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_verified_store(store: dict[str, float]) -> None:
    with open(VERIFIED_SESSIONS_FILE, "w") as f:
        json.dump(store, f)


def consume_verified_session(username: str) -> bool:
    """Returns True and removes the entry if the username completed OTP verification recently."""
    username = username.lower().lstrip("@")
    store = _load_verified_store()
    expires_at = store.get(username)
    if expires_at and time.time() < expires_at:
        store.pop(username, None)
        _save_verified_store(store)
        return True
    if username in store:
        store.pop(username, None)
        _save_verified_store(store)
    return False

router = APIRouter(tags=["auth"])

async def _on_token_arrived(token: str, chat_id: int) -> None:
    """Bot tokenni qabul qilganda OTP ni yuboradi."""
    entry = _pending_tokens.get(token)
    if not entry:
        return
    phone_hash, otp_code, expires_at = entry
    if time.time() > expires_at:
        _pending_tokens.pop(token, None)
        return
    sent = await send_otp_to_chat(chat_id, otp_code)
    if sent:
        _phone_otp_store[phone_hash] = (otp_code, expires_at, 0)
        _pending_tokens.pop(token, None)

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
    if get_chat_id_by_phone_hash(phone_hash):
        sent = await send_otp_by_phone_hash(phone_hash, otp_code)
        if sent:
            _phone_otp_store[phone_hash] = (otp_code, expires_at, 0)
            return {
                "token": None,
                "bot_username": BOT_USERNAME,
                "expires_in": OTP_TTL_SECONDS,
                "direct": True,   # ilova deeplink ochmasin, kod yuborildi
            }

    # Aks holda — token orqali deeplink flow
    _pending_tokens[token] = (phone_hash, otp_code, expires_at)
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

    entry = _phone_otp_store.get(phone_hash)
    if not entry:
        raise HTTPException(status_code=400, detail=E.OTP_NOT_FOUND)

    code, expires_at, attempts = entry
    if time.time() > expires_at:
        _phone_otp_store.pop(phone_hash, None)
        raise HTTPException(status_code=400, detail=E.OTP_EXPIRED)

    if attempts >= OTP_MAX_ATTEMPTS:
        _phone_otp_store.pop(phone_hash, None)
        raise HTTPException(status_code=429, detail=E.OTP_TOO_MANY_ATTEMPTS)

    if body.code != code:
        _phone_otp_store[phone_hash] = (code, expires_at, attempts + 1)
        raise HTTPException(status_code=400, detail=E.OTP_INVALID)

    _phone_otp_store.pop(phone_hash, None)
    # Verified session saqlash (username o'rniga phone_hash ishlatamiz)
    store = _load_verified_store()
    store[phone_hash] = time.time() + VERIFIED_TTL_SECONDS
    _save_verified_store(store)
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

    if not get_chat_id(username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=E.TELEGRAM_USER_NOT_FOUND,
        )

    code = str(random.randint(100000, 999999))
    _otp_store[username] = (code, time.time() + OTP_TTL_SECONDS, 0)

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

    entry = _otp_store.get(username)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.OTP_NOT_FOUND)

    code, expires_at, attempts = entry
    if time.time() > expires_at:
        _otp_store.pop(username, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.OTP_EXPIRED)

    if attempts >= OTP_MAX_ATTEMPTS:
        _otp_store.pop(username, None)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=E.OTP_TOO_MANY_ATTEMPTS)

    if body.code != code:
        _otp_store[username] = (code, expires_at, attempts + 1)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=E.OTP_INVALID)

    # Consume the OTP so it can't be reused
    _otp_store.pop(username, None)
    # Mark username as verified so registration can proceed (persisted to survive server restarts)
    store = _load_verified_store()
    store[username] = time.time() + VERIFIED_TTL_SECONDS
    _save_verified_store(store)
    return {"detail": "OTP verified successfully."}
