"""
AES-256-GCM shifrlash va HMAC-SHA256 deterministik hash.

Muhim maydonlar: phone, tin, telegram_username

  encrypt(text)       → shifrlangan string (base64)
  decrypt(blob)       → asl matn
  hmac_hash(value)    → deterministik hash (DB lookup + JWT sub uchun)
"""
import os
import base64
import hmac as _hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# .env dan o'qiladi; ishlab chiqarishda albatta o'rnatilishi shart
_enc_hex  = os.getenv("ENCRYPTION_KEY", "")
_hmac_secret = os.getenv("HMAC_KEY", "change_this_hmac_secret_in_production").encode()

if _enc_hex and len(_enc_hex) == 64:
    _key = bytes.fromhex(_enc_hex)
else:
    # Dev rejimi — har restart'da yangi kalit (eskilarni o'qib bo'lmaydi)
    import logging
    logging.warning("[ENCRYPTION] ENCRYPTION_KEY not set — generating ephemeral key (dev only!)")
    _key = AESGCM.generate_key(bit_length=256)

_aesgcm = AESGCM(_key)

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
