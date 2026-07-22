from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query

from typing import Optional
from datetime import datetime, timezone
import uuid

from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import models
from db import AsyncSessionLocal, get_db
from core.dependencies import get_current_user
from core.security import SECRET_KEY, ALGORITHM
from core.websocket import chat_manager
from core.errors import E


def _msg_dict(msg: models.ChatMessage) -> dict:
    """Serialize a ChatMessage row to a plain JSON-safe dict."""
    return {
        "id": str(msg.id),
        "chat_id": str(msg.conversation_id),
        "sender_id": str(msg.sender_id),
        "text": msg.content,
        "timestamp": msg.sent_at.isoformat() if msg.sent_at else None,
    }


def _parse_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


async def _get_chat_by_id(db: AsyncSession, chat_id: str) -> Optional[models.Chat]:
    """Fetch a Chat by its UUID, returning None for invalid/missing IDs."""
    cid = _parse_uuid(chat_id)
    if cid is None:
        return None
    return await db.get(models.Chat, cid)

router = APIRouter(tags=["chat"])

@router.get("/chats/")
async def get_chats(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.Chat)
        .where(or_(models.Chat.user_id == current_user.id, models.Chat.other_user_id == current_user.id))
        .order_by(models.Chat.last_message_time.desc())
    )
    chats = result.scalars().all()

    # Batch-load all other users to avoid N+1 queries
    other_user_ids = [
        chat.other_user_id if chat.user_id == current_user.id else chat.user_id
        for chat in chats
    ]
    other_users_map: dict = {}
    if other_user_ids:
        users_result = await db.execute(select(models.User).where(models.User.id.in_(other_user_ids)))
        other_users_map = {u.id: u for u in users_result.scalars().all()}

    result_list = []
    for chat in chats:
        other_user_id = chat.other_user_id if chat.user_id == current_user.id else chat.user_id
        other_user = other_users_map.get(other_user_id)
        if not other_user:
            continue

        result_list.append({
            "id": str(chat.id),
            "other_user": {
                "id": str(other_user.id),
                "name": other_user.name,
                "avatar": other_user.avatar,
                "role": other_user.role
            },
            "last_message": chat.last_message,
            "last_message_time": chat.last_message_time,
            "unread_count": chat.unread_count if chat.user_id == current_user.id else 0,
            "product_id": str(chat.product_id) if chat.product_id else None
        })

    return result_list

@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await _get_chat_by_id(db, chat_id)
    if chat and chat.user_id != current_user.id and chat.other_user_id != current_user.id:
        chat = None

    if not chat:
        raise HTTPException(status_code=404, detail=E.CHAT_NOT_FOUND)

    result = await db.execute(
        select(models.ChatMessage)
        .where(models.ChatMessage.conversation_id == chat.id)
        .order_by(models.ChatMessage.sent_at.asc())
    )
    messages = result.scalars().all()

    return [_msg_dict(msg) for msg in messages]

@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: str,
    message_text: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await _get_chat_by_id(db, chat_id)
    if chat and chat.user_id != current_user.id and chat.other_user_id != current_user.id:
        chat = None

    if not chat:
        raise HTTPException(status_code=404, detail=E.CHAT_NOT_FOUND)

    new_message = models.ChatMessage(
        conversation_id=chat.id,
        sender_id=current_user.id,
        content=message_text,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(new_message)

    chat.last_message = message_text
    chat.last_message_time = datetime.now(timezone.utc)

    if chat.user_id != current_user.id:
        chat.unread_count += 1

    await db.commit()
    await db.refresh(new_message)

    return _msg_dict(new_message)

@router.post("/chats/{chat_id}/mark-read")
async def mark_chat_as_read(
    chat_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await _get_chat_by_id(db, chat_id)
    if chat and chat.user_id != current_user.id:
        chat = None

    if not chat:
        raise HTTPException(status_code=404, detail=E.CHAT_PERMISSION_DENIED)

    old_count = chat.unread_count
    chat.unread_count = 0
    await db.commit()

    return {"message": "Chat marked as read", "previous_unread_count": old_count}

@router.post("/chats/")
async def create_chat(
    other_user_id: str,
    product_id: Optional[str] = None,
    initial_message: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    other_uid = _parse_uuid(other_user_id)
    if other_uid is None:
        raise HTTPException(status_code=404, detail=E.CHAT_NOT_FOUND)

    result = await db.execute(
        select(models.Chat).where(
            or_(
                (models.Chat.user_id == current_user.id) & (models.Chat.other_user_id == other_uid),
                (models.Chat.user_id == other_uid) & (models.Chat.other_user_id == current_user.id),
            )
        )
    )
    existing_chat = result.scalars().first()

    if existing_chat:
        return {"chat_id": str(existing_chat.id), "existing": True}

    new_chat = models.Chat(
        user_id=current_user.id,
        other_user_id=other_uid,
        product_id=_parse_uuid(product_id) if product_id else None,
        last_message=initial_message or "",
        last_message_time=datetime.now(timezone.utc),
        unread_count=0,
    )
    db.add(new_chat)
    await db.flush()

    if initial_message:
        message = models.ChatMessage(
            conversation_id=new_chat.id,
            sender_id=current_user.id,
            content=initial_message,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(message)

    await db.commit()

    return {"chat_id": str(new_chat.id), "existing": False}

@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    chat_id: str,
    token: str = Query(...),
):
    # Authenticate via JWT token query param — never trust URL user_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        if not phone:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.User).where(models.User.phone_hash == phone))
        user = result.scalar_one_or_none()
        if not user:
            await websocket.close(code=4001)
            return

        # Verify the user belongs to this chat
        chat = await _get_chat_by_id(db, chat_id)
        if not chat or (chat.user_id != user.id and chat.other_user_id != user.id):
            await websocket.close(code=4003)
            return

        user_id = user.id

    await chat_manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Basic message length guard
            if len(data) > 4000:
                continue
            try:
                async with AsyncSessionLocal() as db:
                    new_message = models.ChatMessage(
                        conversation_id=uuid.UUID(chat_id),
                        sender_id=user_id,
                        content=data,
                        sent_at=datetime.now(timezone.utc),
                    )
                    db.add(new_message)

                    chat = await db.get(models.Chat, uuid.UUID(chat_id))
                    if chat:
                        chat.last_message = data
                        chat.last_message_time = datetime.now(timezone.utc)
                        if chat.user_id != user_id:
                            chat.unread_count += 1
                    await db.commit()
            except Exception as e:
                print(f"Error saving websocket message: {e}")

            await chat_manager.broadcast(chat_id, f"{user_id}:{data}", websocket)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_id, websocket)
