"""
Unit tests — Server shart emas, to'g'ridan Python modullari test qilinadi.

Qamrab olinganlar:
  - core/encryption.py  : encrypt/decrypt/hmac_hash round-trip
  - services/wallet_service.py : credit/debit mantiq (mock bilan)
  - services/audit_service.py  : log yozilishi (mock bilan)
  - core/errors.py       : barcha kodlar to'g'ri format
  - core/storage.py      : _r2_configured() toggle

Ishga tushirish (server kerak emas):
    cd tests/backend
    pytest test_unit.py -v
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit  # server talab qilinmaydi

# Backend modullarini import qilish uchun path qo'shish
_BACKEND = os.path.join(os.path.dirname(__file__), "../../android_app/backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ── Encryption ────────────────────────────────────────────────────────────────

class TestEncryption:
    def setup_method(self):
        # Test uchun muhit o'zgaruvchilarini sozlash
        os.environ.setdefault("ENCRYPTION_KEY", "A" * 32)
        os.environ.setdefault("HMAC_KEY", "B" * 32)

    def test_encrypt_decrypt_roundtrip(self):
        from core.encryption import encrypt, decrypt
        original = "+998901234567"
        ciphertext = encrypt(original)
        assert ciphertext != original
        assert ciphertext.startswith("enc:")
        assert decrypt(ciphertext) == original

    def test_different_plaintexts_produce_different_ciphertexts(self):
        from core.encryption import encrypt
        c1 = encrypt("hello")
        c2 = encrypt("world")
        assert c1 != c2

    def test_same_plaintext_different_ciphertexts(self):
        """AES-GCM har safar turli nonce ishlatadi."""
        from core.encryption import encrypt
        c1 = encrypt("same")
        c2 = encrypt("same")
        assert c1 != c2

    def test_hmac_hash_deterministic(self):
        from core.encryption import hmac_hash
        h1 = hmac_hash("+998901234567")
        h2 = hmac_hash("+998901234567")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_inputs_different_hmac(self):
        from core.encryption import hmac_hash
        h1 = hmac_hash("phone1")
        h2 = hmac_hash("phone2")
        assert h1 != h2

    def test_decrypt_non_encrypted_returns_original(self):
        """enc: prefiksi yo'q bo'lsa, o'zini qaytaradi."""
        from core.encryption import decrypt
        plain = "not_encrypted"
        assert decrypt(plain) == plain

    def test_empty_string_encrypt_decrypt(self):
        from core.encryption import encrypt, decrypt
        assert decrypt(encrypt("")) == ""


# ── Error codes ───────────────────────────────────────────────────────────────

class TestErrorCodes:
    def test_all_error_codes_start_with_errors_prefix(self):
        from core.errors import E
        for attr in dir(E):
            if attr.startswith("_"):
                continue
            val = getattr(E, attr)
            if isinstance(val, str):
                assert val.startswith("errors."), \
                    f"E.{attr} = '{val}' — 'errors.' prefiksi yo'q"

    def test_no_duplicate_error_codes(self):
        from core.errors import E
        values = [
            getattr(E, a) for a in dir(E)
            if not a.startswith("_") and isinstance(getattr(E, a), str)
        ]
        assert len(values) == len(set(values)), "Takroriy error kodlar topildi"

    def test_specific_codes_exist(self):
        from core.errors import E
        required = [
            "OTP_NOT_FOUND", "OTP_EXPIRED", "OTP_INVALID",
            "INCORRECT_CREDENTIALS", "PHONE_ALREADY_REGISTERED",
            "PRODUCT_NOT_FOUND", "INSUFFICIENT_FUNDS", "PAYMENT_DECLINED",
            "BUYER_ONLY_REVIEWS", "REVIEW_ALREADY_EXISTS",
        ]
        for name in required:
            assert hasattr(E, name), f"E.{name} topilmadi"


# ── Storage ───────────────────────────────────────────────────────────────────

class TestStorage:
    def test_r2_not_configured_by_default(self):
        """R2 env vars yo'q bo'lsa _r2_configured() False qaytaradi."""
        env_backup = {}
        r2_keys = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID",
                   "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"]
        for k in r2_keys:
            env_backup[k] = os.environ.pop(k, None)
        try:
            # Module'ni qayta yuklash kerak bo'lishi mumkin, lekin funksiya runtime check qiladi
            from core.storage import _r2_configured
            assert _r2_configured() is False
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

    def test_r2_configured_when_env_vars_set(self):
        os.environ["R2_ACCOUNT_ID"]        = "test-account"
        os.environ["R2_ACCESS_KEY_ID"]     = "test-key"
        os.environ["R2_SECRET_ACCESS_KEY"] = "test-secret"
        os.environ["R2_BUCKET_NAME"]       = "test-bucket"
        try:
            from core.storage import _r2_configured
            assert _r2_configured() is True
        finally:
            for k in ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID",
                      "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"]:
                os.environ.pop(k, None)


# ── Wallet service ────────────────────────────────────────────────────────────

class TestWalletServiceLogic:
    """
    wallet_service.credit() va debit() mantiqini mock User bilan tekshiradi.
    MongoDB ulanishi shart emas.
    """

    @pytest.mark.asyncio
    async def test_credit_increases_balance(self):
        from services import wallet_service

        user = MagicMock()
        user.balance = 100.0
        user.save = AsyncMock()

        await wallet_service.credit(
            user=user, amount=50.0,
            card_token="tok_test", idempotency_key="key-1"
        )
        assert user.balance == 150.0
        user.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debit_decreases_balance(self):
        from services import wallet_service

        user = MagicMock()
        user.balance = 200.0
        user.save = AsyncMock()

        await wallet_service.debit(user=user, amount=75.0, card_token="tok_test")
        assert user.balance == 125.0
        user.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_debit_cannot_go_negative(self):
        from services import wallet_service

        user = MagicMock()
        user.balance = 10.0
        user.save = AsyncMock()

        with pytest.raises(Exception):
            await wallet_service.debit(user=user, amount=100.0, card_token="tok_test")


# ── Cache module ──────────────────────────────────────────────────────────────

class TestCacheModule:
    @pytest.mark.asyncio
    async def test_cache_get_returns_none_without_redis(self):
        from core import cache
        # Redis yo'q holatini simulyatsiya
        original = cache._redis
        cache._redis = None
        try:
            result = await cache.cache_get("test_key")
            assert result is None
        finally:
            cache._redis = original

    @pytest.mark.asyncio
    async def test_cache_set_noop_without_redis(self):
        from core import cache
        original = cache._redis
        cache._redis = None
        try:
            # Xato chiqarmasligi kerak
            await cache.cache_set("test_key", {"data": 1}, ttl=60)
        finally:
            cache._redis = original

    @pytest.mark.asyncio
    async def test_cache_delete_noop_without_redis(self):
        from core import cache
        original = cache._redis
        cache._redis = None
        try:
            await cache.cache_delete("test_key")
        finally:
            cache._redis = original

    def test_ttl_constants_reasonable(self):
        from core.cache import CATEGORIES_TTL, PRODUCTS_TTL, PROFILE_TTL, REVIEWS_TTL, RECS_TTL
        assert CATEGORIES_TTL >= 3600   # kamida 1 soat
        assert PRODUCTS_TTL   >= 60     # kamida 1 daqiqa
        assert PROFILE_TTL    >= 300    # kamida 5 daqiqa
        assert REVIEWS_TTL    >= 60
        assert RECS_TTL       >= 1800   # kamida 30 daqiqa
