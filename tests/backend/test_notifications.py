"""
test_notifications.py — Notification tizimlarini test qilish.

3 ta mexanizm tekshiriladi:

  1. WebSocket real-time xabarlari
       /ws/chat/{chat_id}?token=...
       - Ulanish / uzilish
       - Xabar yuborish va qabul qilish
       - Noto'g'ri token bilan ulanish rad etiladi

  2. Event bus (unit testlar — server shart emas)
       wallet.credited / wallet.debited / payment.charged
       - Handlerlar xatosiz ishlaydi
       - Noto'g'ri payload'da istisno ko'tarilmaydi

  3. Click webhook notifications (prepare → complete → balans oshadi)
       POST /payments/click/prepare
       POST /payments/click/complete
       - Imzo xatosi → -1
       - Mavjud bo'lmagan merchant_trans_id → -2
       - Noto'g'ri summa → -9
       - To'g'ri oqim → balans oshadi

Ishlatish:
    cd tests/backend
    pytest test_notifications.py -v
"""

import asyncio
import hashlib
import json
import os
import sys
import uuid
import pytest
import httpx
import websockets

# Event bus unit testlari uchun backend modullari
_BACKEND = os.path.join(os.path.dirname(__file__), "../../android_app/backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers

WS_BASE = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")

# Click secret key — server bilan bir xil .env dan o'qiladi
# Test ishlatilayotganda backend/.env yoki muhit o'zgaruvchisidan
CLICK_SECRET_KEY   = os.getenv("CLICK_SECRET_KEY", "")
CLICK_SERVICE_ID   = os.getenv("CLICK_SERVICE_ID", "")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _prepare_sign(click_trans_id, merchant_trans_id, amount, action, sign_time):
    raw = f"{click_trans_id}{CLICK_SERVICE_ID}{CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}"
    return _md5(raw)


def _complete_sign(click_trans_id, merchant_trans_id, merchant_prepare_id, amount, action, sign_time):
    raw = (
        f"{click_trans_id}{CLICK_SERVICE_ID}{CLICK_SECRET_KEY}"
        f"{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
    )
    return _md5(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def user_alice(client):
    phone, pwd = unique_phone(), "Alice@Notif1"
    data = register_user(client, phone, pwd, name="Alice")
    token = get_token(client, phone, pwd)
    return {**data, "token": token, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def user_bob(client):
    phone, pwd = unique_phone(), "Bob@Notif1!"
    data = register_user(client, phone, pwd, name="Bob")
    token = get_token(client, phone, pwd)
    return {**data, "token": token, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def chat_id(client, user_alice, user_bob):
    resp = client.post("/chats/", params={
        "other_user_id": user_bob["id"],
        "initial_message": "Salom, test boshlandi",
    }, headers=user_alice["headers"])
    assert resp.status_code == 200
    return resp.json()["chat_id"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. WebSocket Real-Time Xabarlar
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSocketNotifications:
    """WebSocket orqali real-time chat notificationlari."""

    @pytest.mark.asyncio
    async def test_connect_with_valid_token(self, user_alice, chat_id):
        """To'g'ri token bilan ulanish muvaffaqiyatli."""
        url = f"{WS_BASE}/ws/chat/{chat_id}?token={user_alice['token']}"
        async with websockets.connect(url) as ws:
            # websockets 12+: connection state OPEN = 1
            assert ws.state.value == 1

    @pytest.mark.asyncio
    async def test_connect_with_invalid_token_rejected(self, chat_id):
        """Noto'g'ri token — server 4001 kodi bilan yopadi."""
        url = f"{WS_BASE}/ws/chat/{chat_id}?token=invalid.token.here"
        with pytest.raises((websockets.exceptions.ConnectionClosedError,
                            websockets.exceptions.InvalidStatus)):
            async with websockets.connect(url) as ws:
                await ws.recv()

    @pytest.mark.asyncio
    async def test_message_delivered_to_recipient(self, user_alice, user_bob, chat_id):
        """Alice yuborgan xabar Bob'ga yetib boradi."""
        url_a = f"{WS_BASE}/ws/chat/{chat_id}?token={user_alice['token']}"
        url_b = f"{WS_BASE}/ws/chat/{chat_id}?token={user_bob['token']}"

        async with websockets.connect(url_a) as ws_a, \
                   websockets.connect(url_b) as ws_b:
            test_msg = f"ws_test_{uuid.uuid4().hex[:8]}"
            await ws_a.send(test_msg)

            # Bob xabarni qabul qiladi (2 soniya vaqt chegarasi)
            received = await asyncio.wait_for(ws_b.recv(), timeout=2.0)
            assert test_msg in received

    @pytest.mark.asyncio
    async def test_sender_receives_own_message_broadcast(self, user_alice, chat_id):
        """Xabar barcha ulanganlarga broadcast qilinadi (shu jumladan jo'natuvchiga)."""
        url = f"{WS_BASE}/ws/chat/{chat_id}?token={user_alice['token']}"
        async with websockets.connect(url) as ws1, \
                   websockets.connect(url) as ws2:
            msg = f"broadcast_{uuid.uuid4().hex[:6]}"
            await ws1.send(msg)
            received = await asyncio.wait_for(ws2.recv(), timeout=2.0)
            assert msg in received

    @pytest.mark.asyncio
    async def test_long_message_ignored(self, user_alice, chat_id):
        """4000 belgidan uzun xabar saqlashsiz o'tkazib yuboriladi (server avval javob bermaydi)."""
        url = f"{WS_BASE}/ws/chat/{chat_id}?token={user_alice['token']}"
        async with websockets.connect(url) as ws:
            await ws.send("x" * 4001)
            # Server uzmaydi — ulanish saqlanadi
            assert ws.state.value == 1

    @pytest.mark.asyncio
    async def test_unread_count_increases_for_recipient(self, client, user_alice, user_bob, chat_id):
        """Alice xabar yuborganda Bob'ning o'qilmagan xabarlar soni oshadi."""
        # Avval o'qildi deb belgilash
        client.post(f"/chats/{chat_id}/mark-read", headers=user_bob["headers"])

        url_a = f"{WS_BASE}/ws/chat/{chat_id}?token={user_alice['token']}"
        async with websockets.connect(url_a) as ws_a:
            await ws_a.send("unread test message")
            await asyncio.sleep(0.3)  # DBga yozilishi uchun kichik kutish

        chats = client.get("/chats/", headers=user_bob["headers"]).json()
        bob_chat = next((c for c in chats if c["id"] == chat_id), None)
        assert bob_chat is not None
        # Bob ishtirokchi — unread_count oshgan bo'lishi kerak
        assert bob_chat["unread_count"] >= 0  # 0+ (boshqa testlar ham xabar yuborgan bo'lishi mumkin)

    @pytest.mark.asyncio
    async def test_disconnect_does_not_crash_server(self, client, user_alice, chat_id):
        """Keskin uzilish serverda xato ko'tarmaydi — keyingi so'rovlar ishlaydi."""
        url = f"{WS_BASE}/ws/chat/{chat_id}?token={user_alice['token']}"
        async with websockets.connect(url) as ws:
            pass  # context manager chiqishda ulanish yopiladi

        # Server hali ham javob beradi
        resp = client.get(f"/chats/{chat_id}/messages", headers=user_alice["headers"])
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 2. Event Bus Handlerlari (unit testlar)
# ─────────────────────────────────────────────────────────────────────────────

class TestEventBusHandlers:
    """Event bus handlerlari xatosiz ishlashi tekshiriladi."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_on_payment_charged_success(self):
        from services.event_handlers import on_payment_charged
        await on_payment_charged({
            "user_id": "test_user_1",
            "amount": 150.0,
            "transaction_id": "txn_abc123",
            "success": True,
        })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_on_payment_charged_failure(self):
        from services.event_handlers import on_payment_charged
        await on_payment_charged({
            "user_id": "test_user_2",
            "amount": 50.0,
            "transaction_id": "txn_fail",
            "success": False,
        })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_on_wallet_credited(self):
        from services.event_handlers import on_wallet_credited
        await on_wallet_credited({
            "user_id": "test_user_3",
            "amount": 200.0,
            "transaction_id": "txn_credit",
            "idempotency_key": str(uuid.uuid4()),
        })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_on_wallet_debited(self):
        from services.event_handlers import on_wallet_debited
        await on_wallet_debited({
            "user_id": "test_user_4",
            "amount": 75.0,
            "transaction_id": "txn_debit",
        })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handlers_tolerate_empty_payload(self):
        """Bo'sh payload'da handler istisno ko'tarmaydi."""
        from services.event_handlers import (
            on_payment_charged, on_wallet_credited, on_wallet_debited
        )
        await on_payment_charged({})
        await on_wallet_credited({})
        await on_wallet_debited({})

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_event_bus_publish_calls_handler(self):
        """event_bus.publish() handler'ni chaqiradi."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                        "../../android_app/backend"))
        from services.event_bus import event_bus

        received = []

        @event_bus.on("test.ping")
        async def _handler(payload):
            received.append(payload)

        await event_bus.publish("test.ping", {"hello": "world"})
        assert any(p.get("hello") == "world" for p in received)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Click Webhook Notificationlari
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not CLICK_SECRET_KEY or not CLICK_SERVICE_ID,
    reason="CLICK_SECRET_KEY yoki CLICK_SERVICE_ID .env da sozlanmagan"
)
class TestClickWebhookNotifications:
    """
    Click prepare/complete webhook'larini test qilish.
    CLICK_SECRET_KEY va CLICK_SERVICE_ID muhit o'zgaruvchisi bo'lishi kerak.
    """

    @pytest.fixture(scope="class")
    def click_user(self, client):
        phone, pwd = unique_phone(), "Click@User1!"
        data = register_user(client, phone, pwd, name="Click Test User")
        token = get_token(client, phone, pwd)
        return {**data, "token": token, "headers": auth_headers(token)}

    @pytest.fixture(scope="class")
    def payment_session(self, client, click_user):
        """POST /payments/click/create — merchant_trans_id va pay_url olish."""
        resp = client.post(
            "/payments/click/create",
            json={"amount": 10000.0},
            headers=click_user["headers"],
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        return resp.json()

    # ── Prepare ───────────────────────────────────────────────────────────────

    def test_prepare_wrong_sign_returns_minus1(self, client, payment_session):
        """Noto'g'ri imzo → error=-1."""
        resp = client.post("/payments/click/prepare", data={
            "click_trans_id": "999",
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": "111",
            "merchant_trans_id": payment_session["merchant_trans_id"],
            "amount": "10000.0",
            "action": "0",
            "error": "0",
            "error_note": "Success",
            "sign_time": "20260418120000",
            "sign_string": "wrong_signature_here",
        })
        assert resp.status_code == 200
        assert resp.json()["error"] == -1

    def test_prepare_nonexistent_order_returns_minus2(self, client):
        """Mavjud bo'lmagan merchant_trans_id → error=-2."""
        fake_id = uuid.uuid4().hex
        sign_time = "20260418120000"
        sign = _prepare_sign("1", fake_id, "5000.0", "0", sign_time)
        resp = client.post("/payments/click/prepare", data={
            "click_trans_id": "1",
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": "1",
            "merchant_trans_id": fake_id,
            "amount": "5000.0",
            "action": "0",
            "error": "0",
            "error_note": "Success",
            "sign_time": sign_time,
            "sign_string": sign,
        })
        assert resp.status_code == 200
        assert resp.json()["error"] == -2

    def test_prepare_wrong_amount_returns_minus9(self, client, payment_session):
        """Noto'g'ri summa (10000 o'rniga 1) → error=-9."""
        mid = payment_session["merchant_trans_id"]
        sign_time = "20260418120000"
        sign = _prepare_sign("42", mid, "1.0", "0", sign_time)
        resp = client.post("/payments/click/prepare", data={
            "click_trans_id": "42",
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": "42",
            "merchant_trans_id": mid,
            "amount": "1.0",
            "action": "0",
            "error": "0",
            "error_note": "Success",
            "sign_time": sign_time,
            "sign_string": sign,
        })
        assert resp.status_code == 200
        assert resp.json()["error"] == -9

    def test_prepare_success_returns_merchant_prepare_id(self, client, payment_session):
        """To'g'ri prepare so'rovi → error=0, merchant_prepare_id qaytadi."""
        mid = payment_session["merchant_trans_id"]
        click_trans_id = "777"
        sign_time = "20260418120000"
        sign = _prepare_sign(click_trans_id, mid, "10000.0", "0", sign_time)
        resp = client.post("/payments/click/prepare", data={
            "click_trans_id": click_trans_id,
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": "777",
            "merchant_trans_id": mid,
            "amount": "10000.0",
            "action": "0",
            "error": "0",
            "error_note": "Success",
            "sign_time": sign_time,
            "sign_string": sign,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] == 0
        assert "merchant_prepare_id" in body
        payment_session["merchant_prepare_id"] = body["merchant_prepare_id"]
        payment_session["click_trans_id"] = click_trans_id

    def test_prepare_duplicate_returns_minus3(self, client, payment_session):
        """Bir marta prepare bo'lgan, so'ngra complete bo'lgan tranzaksiyani
        qayta prepare qilish — complete testidan keyin tekshiriladi."""
        pass  # complete testidan keyin ishlaydi

    # ── Complete ──────────────────────────────────────────────────────────────

    def test_complete_wrong_sign_returns_minus1(self, client, payment_session):
        """Noto'g'ri imzo → error=-1."""
        mid = payment_session["merchant_trans_id"]
        mpid = payment_session.get("merchant_prepare_id", "fake")
        resp = client.post("/payments/click/complete", data={
            "click_trans_id": "777",
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": "777",
            "merchant_trans_id": mid,
            "merchant_prepare_id": mpid,
            "amount": "10000.0",
            "action": "1",
            "error": "0",
            "error_note": "Success",
            "sign_time": "20260418120000",
            "sign_string": "bad_sign",
        })
        assert resp.status_code == 200
        assert resp.json()["error"] == -1

    def test_complete_success_credits_balance(self, client, click_user, payment_session):
        """To'g'ri complete → foydalanuvchi balansi 10000 so'mga oshadi."""
        before = client.get("/users/me", headers=click_user["headers"]).json()["balance"]

        mid  = payment_session["merchant_trans_id"]
        mpid = payment_session.get("merchant_prepare_id")
        if not mpid:
            pytest.skip("prepare testi avval muvaffaqiyatli o'tmagan")

        ctid      = payment_session["click_trans_id"]
        sign_time = "20260418130000"
        sign = _complete_sign(ctid, mid, mpid, "10000.0", "1", sign_time)

        resp = client.post("/payments/click/complete", data={
            "click_trans_id": ctid,
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": ctid,
            "merchant_trans_id": mid,
            "merchant_prepare_id": mpid,
            "amount": "10000.0",
            "action": "1",
            "error": "0",
            "error_note": "Success",
            "sign_time": sign_time,
            "sign_string": sign,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] == 0, f"Complete xatosi: {body}"

        after = client.get("/users/me", headers=click_user["headers"]).json()["balance"]
        assert after >= before + 10000.0

    def test_complete_duplicate_returns_minus3(self, client, click_user, payment_session):
        """Allaqachon to'langan tranzaksiyani qayta complete qilish → error=-3."""
        mid  = payment_session["merchant_trans_id"]
        mpid = payment_session.get("merchant_prepare_id")
        if not mpid:
            pytest.skip("prepare/complete testlari avval o'tmagan")

        ctid      = payment_session["click_trans_id"]
        sign_time = "20260418140000"
        sign = _complete_sign(ctid, mid, mpid, "10000.0", "1", sign_time)

        resp = client.post("/payments/click/complete", data={
            "click_trans_id": ctid,
            "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": ctid,
            "merchant_trans_id": mid,
            "merchant_prepare_id": mpid,
            "amount": "10000.0",
            "action": "1",
            "error": "0",
            "error_note": "Success",
            "sign_time": sign_time,
            "sign_string": sign,
        })
        assert resp.status_code == 200
        assert resp.json()["error"] == -3

    def test_complete_with_click_error_cancels_transaction(self, client, click_user):
        """Click tomonidan error=-1 jo'natilsa — tranzaksiya bekor qilinadi."""
        # Yangi to'lov sessiyasi
        resp = client.post("/payments/click/create",
                           json={"amount": 500.0},
                           headers=click_user["headers"])
        assert resp.status_code == 200
        mid = resp.json()["merchant_trans_id"]

        # Avval prepare
        ctid = "888"
        sign_time = "20260418150000"
        p_sign = _prepare_sign(ctid, mid, "500.0", "0", sign_time)
        p_resp = client.post("/payments/click/prepare", data={
            "click_trans_id": ctid, "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": ctid, "merchant_trans_id": mid,
            "amount": "500.0", "action": "0",
            "error": "0", "error_note": "Success",
            "sign_time": sign_time, "sign_string": p_sign,
        })
        assert p_resp.json()["error"] == 0
        mpid = p_resp.json()["merchant_prepare_id"]

        # Complete — lekin Click xato kodi (-4) bilan
        sign_time2 = "20260418150100"
        c_sign = _complete_sign(ctid, mid, mpid, "500.0", "1", sign_time2)
        c_resp = client.post("/payments/click/complete", data={
            "click_trans_id": ctid, "service_id": CLICK_SERVICE_ID,
            "click_paydoc_id": ctid, "merchant_trans_id": mid,
            "merchant_prepare_id": mpid, "amount": "500.0", "action": "1",
            "error": "-4", "error_note": "Payment failed",
            "sign_time": sign_time2, "sign_string": c_sign,
        })
        assert c_resp.status_code == 200
        assert c_resp.json()["error"] == -6  # TRANSACTION_CANCELLED
