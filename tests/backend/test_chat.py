"""
QA tests — Chat & Messaging endpoints
    POST /chats/
    GET  /chats/
    GET  /chats/{id}/messages
    POST /chats/{id}/messages
    POST /chats/{id}/mark-read
"""

import pytest
import httpx

from conftest import BASE_URL, unique_phone, register_user, get_token, auth_headers


# ── Module-scoped fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def user_a(client):
    phone = unique_phone()
    password = "UserA@Chat1"
    data = register_user(client, phone, password, name="Chat User A")
    token = get_token(client, phone, password)
    return {**data, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def user_b(client):
    phone = unique_phone()
    password = "UserB@Chat1"
    data = register_user(client, phone, password, name="Chat User B")
    token = get_token(client, phone, password)
    return {**data, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def user_c(client):
    """A third user who is not party to the A-B chat."""
    phone = unique_phone()
    password = "UserC@Chat1"
    data = register_user(client, phone, password, name="Chat User C")
    token = get_token(client, phone, password)
    return {**data, "headers": auth_headers(token)}


@pytest.fixture(scope="module")
def chat_id(client, user_a, user_b):
    resp = client.post("/chats/", params={
        "other_user_id": user_b["id"],
        "initial_message": "Hello from QA",
    }, headers=user_a["headers"])
    assert resp.status_code == 200
    return resp.json()["chat_id"]


# ── POST /chats/ ──────────────────────────────────────────────────────────────

class TestCreateChat:
    def test_creates_new_chat(self, client, user_a, user_b, chat_id):
        assert chat_id is not None

    def test_response_has_chat_id_and_existing_flag(self, client, user_a, user_b):
        resp = client.post("/chats/", params={"other_user_id": user_b["id"]},
                           headers=user_a["headers"])
        body = resp.json()
        assert "chat_id" in body
        assert "existing" in body

    def test_second_request_returns_existing_true(self, client, user_a, user_b):
        resp = client.post("/chats/", params={"other_user_id": user_b["id"]},
                           headers=user_a["headers"])
        assert resp.json()["existing"] is True

    def test_initial_message_stored(self, client, user_a, chat_id):
        resp = client.get(f"/chats/{chat_id}/messages", headers=user_a["headers"])
        assert resp.status_code == 200
        texts = [m["text"] for m in resp.json()]
        assert "Hello from QA" in texts

    def test_unauthenticated_create_returns_401(self, client, user_b):
        resp = client.post("/chats/", params={"other_user_id": user_b["id"]})
        assert resp.status_code == 401


# ── GET /chats/ ───────────────────────────────────────────────────────────────

class TestListChats:
    def test_user_can_list_their_chats(self, client, user_a, chat_id):
        resp = client.get("/chats/", headers=user_a["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_chat_appears_in_both_participants_lists(self, client, user_a, user_b, chat_id):
        ids_a = [c["id"] for c in client.get("/chats/", headers=user_a["headers"]).json()]
        ids_b = [c["id"] for c in client.get("/chats/", headers=user_b["headers"]).json()]
        assert chat_id in ids_a
        assert chat_id in ids_b

    def test_chat_list_item_has_required_fields(self, client, user_a):
        resp = client.get("/chats/", headers=user_a["headers"])
        if resp.json():
            chat = resp.json()[0]
            for field in ("id", "other_user", "last_message"):
                assert field in chat

    def test_new_user_has_empty_chat_list(self, client):
        phone = unique_phone()
        password = "Empty@Chat1"
        register_user(client, phone, password)
        token = get_token(client, phone, password)
        resp = client.get("/chats/", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated_list_returns_401(self, client):
        resp = client.get("/chats/")
        assert resp.status_code == 401


# ── GET /chats/{id}/messages ──────────────────────────────────────────────────

class TestGetMessages:
    def test_participant_can_fetch_messages(self, client, user_a, chat_id):
        resp = client.get(f"/chats/{chat_id}/messages", headers=user_a["headers"])
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_other_participant_can_also_fetch(self, client, user_b, chat_id):
        resp = client.get(f"/chats/{chat_id}/messages", headers=user_b["headers"])
        assert resp.status_code == 200

    def test_non_participant_cannot_fetch_messages(self, client, user_c, chat_id):
        resp = client.get(f"/chats/{chat_id}/messages", headers=user_c["headers"])
        assert resp.status_code == 404

    def test_messages_have_required_fields(self, client, user_a, chat_id):
        resp = client.get(f"/chats/{chat_id}/messages", headers=user_a["headers"])
        if resp.json():
            msg = resp.json()[0]
            for field in ("chat_id", "sender_id", "text", "timestamp"):
                assert field in msg

    def test_nonexistent_chat_returns_404(self, client, user_a):
        resp = client.get("/chats/000000000000000000000000/messages", headers=user_a["headers"])
        assert resp.status_code == 404

    def test_unauthenticated_fetch_returns_401(self, client, chat_id):
        resp = client.get(f"/chats/{chat_id}/messages")
        assert resp.status_code == 401


# ── POST /chats/{id}/messages ─────────────────────────────────────────────────

class TestSendMessage:
    def test_participant_can_send_message(self, client, user_a, chat_id):
        resp = client.post(f"/chats/{chat_id}/messages",
                           params={"message_text": "Test message from A"},
                           headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.json()["text"] == "Test message from A"

    def test_other_participant_can_reply(self, client, user_b, chat_id):
        resp = client.post(f"/chats/{chat_id}/messages",
                           params={"message_text": "Reply from B"},
                           headers=user_b["headers"])
        assert resp.status_code == 200

    def test_message_appears_in_history(self, client, user_a, chat_id):
        client.post(f"/chats/{chat_id}/messages",
                    params={"message_text": "Unique msg xyz987"},
                    headers=user_a["headers"])
        msgs = client.get(f"/chats/{chat_id}/messages", headers=user_a["headers"]).json()
        texts = [m["text"] for m in msgs]
        assert "Unique msg xyz987" in texts

    def test_non_participant_cannot_send_message(self, client, user_c, chat_id):
        resp = client.post(f"/chats/{chat_id}/messages",
                           params={"message_text": "Intruder message"},
                           headers=user_c["headers"])
        assert resp.status_code == 404

    def test_send_to_nonexistent_chat_returns_404(self, client, user_a):
        resp = client.post("/chats/000000000000000000000000/messages",
                           params={"message_text": "Lost message"},
                           headers=user_a["headers"])
        assert resp.status_code == 404

    def test_unauthenticated_send_returns_401(self, client, chat_id):
        resp = client.post(f"/chats/{chat_id}/messages",
                           params={"message_text": "Ghost message"})
        assert resp.status_code == 401


# ── POST /chats/{id}/mark-read ────────────────────────────────────────────────

class TestMarkRead:
    def test_mark_chat_as_read_returns_200(self, client, user_a, chat_id):
        resp = client.post(f"/chats/{chat_id}/mark-read", headers=user_a["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert "previous_unread_count" in body

    def test_unread_count_becomes_zero_after_mark_read(self, client, user_a, chat_id):
        client.post(f"/chats/{chat_id}/mark-read", headers=user_a["headers"])
        chats = client.get("/chats/", headers=user_a["headers"]).json()
        chat = next((c for c in chats if c["id"] == chat_id), None)
        if chat:
            assert chat["unread_count"] == 0

    def test_non_owner_cannot_mark_chat_as_read(self, client, user_b, chat_id):
        # user_b is other_user_id — mark-read is restricted to the chat creator
        resp = client.post(f"/chats/{chat_id}/mark-read", headers=user_b["headers"])
        assert resp.status_code == 404

    def test_nonexistent_chat_mark_read_returns_404(self, client, user_a):
        resp = client.post("/chats/000000000000000000000000/mark-read", headers=user_a["headers"])
        assert resp.status_code == 404

    def test_unauthenticated_mark_read_returns_401(self, client, chat_id):
        resp = client.post(f"/chats/{chat_id}/mark-read")
        assert resp.status_code == 401
