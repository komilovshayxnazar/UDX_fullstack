"""
AES-256-GCM encryption + HMAC-SHA256 deterministic hash.

Sensitive fields: phone, tin, telegram_username

  encrypt(text)       → encrypted string (base64)
  decrypt(blob)       → plaintext
  hmac_hash(value)    → deterministic hash (DB lookup + JWT sub)

Both keys MUST be set when ENVIRONMENT=production. An ephemeral key is
generated only when ENVIRONMENT is not production so local dev doesn't
need any setup, but in that mode all previously-encrypted values become
unreadable on every restart.
"""
import logging
import os
import base64
import hmac as _hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IS_PROD = os.getenv("ENVIRONMENT", "production").lower() == "production"

# ── AES-256-GCM key ──────────────────────────────────────────────────────
_enc_hex = os.getenv("ENCRYPTION_KEY", "").strip()
if _enc_hex:
    if len(_enc_hex) != 64:
        raise RuntimeError(
            "[ENCRYPTION] ENCRYPTION_KEY must be 64 hex chars (32 bytes)"
        )
    _key = bytes.fromhex(_enc_hex)
elif _IS_PROD:
    raise RuntimeError(
        "[ENCRYPTION] ENCRYPTION_KEY is required when ENVIRONMENT=production"
    )
else:
    logging.warning(
        "[ENCRYPTION] ENCRYPTION_KEY not set — generating ephemeral key (dev only!)"
    )
    _key = AESGCM.generate_key(bit_length=256)

_aesgcm = AESGCM(_key)

# ── HMAC secret ──────────────────────────────────────────────────────────
_hmac_raw = os.getenv("HMAC_KEY", "").strip()
if not _hmac_raw:
    if _IS_PROD:
        raise RuntimeError(
            "[ENCRYPTION] HMAC_KEY is required when ENVIRONMENT=production"
        )
    logging.warning(
        "[ENCRYPTION] HMAC_KEY not set — using ephemeral dev secret"
    )
    _hmac_raw = "dev-only-hmac-key-not-safe-for-production"
_hmac_secret = _hmac_raw.encode()

_PREFIX = "enc:"   # shifrlangan qiymatni oddiy satrdan ajratish uchun


def encrypt(plaintext: str) -> str:
    """Matnni AES-256-GCM bilan shifrlaydi. Qaytaradi: 'enc:<base64>'"""
    nonce = os.urandom(12)
    ct    = _aesgcm.encrypt(nonce, plaintext.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ct).decode()


def decrypt(blob: str) -> str:
    """'enc:<base64>' ni asl matnga qaytaradi."""
    if not blob.startswith(_PREFIX):
        return blob   # allaqachon oddiy matn (migration bosqichi uchun)
    raw   = base64.b64decode(blob[len(_PREFIX):].encode())
    nonce = raw[:12]
    ct    = raw[12:]
    return _aesgcm.decrypt(nonce, ct, None).decode()


def hmac_hash(value: str) -> str:
    """
    Deterministik HMAC-SHA256 hash.
    Bir xil qiymat → har doim bir xil hash.
    DB indeksi va JWT 'sub' maydoni uchun ishlatiladi.
    """
    return _hmac.new(_hmac_secret, value.encode(), hashlib.sha256).hexdigest()


def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX)
