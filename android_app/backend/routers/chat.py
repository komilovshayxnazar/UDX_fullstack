from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query

from typing import Optional
from datetime import datetime

from beanie import PydanticObjectId
from jose import JWTError, jwt

import models
from core.dependencies import get_current_user
from core.security import SECRET_KEY, ALGORITHM
from core.websocket import chat_manager
from core.errors import E


def _msg_dict(msg: models.Message) -> dict:
    """Serialize a Message document to a plain JSON-safe dict."""
    return {
        "id": str(msg.id),
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "text": msg.text,
        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
    }


async def _get_chat_by_id(chat_id: str) -> Optional[models.Chat]:
    """Fetch a Chat by its string ObjectId, returning None for invalid/missing IDs."""
    try:
        PydanticObjectId(chat_id)  # validate format before querying
    except Exception:
        return None
    return await models.Chat.get(chat_id)

router = APIRouter(tags=["chat"])

@router.get("/chats/")
async def get_chats(current_user: models.User = Depends(get_current_user)):
    chats = await models.Chat.find(
        {"$or": [{"user_id": str(current_user.id)}, {"other_user_id": str(current_user.id)}]}
    ).sort("-last_message_time").to_list()
    
    # Batch-load all other users to avoid N+1 queries
    other_user_ids = [
        chat.other_user_id if str(chat.user_id) == str(current_user.id) else chat.user_id
        for chat in chats
    ]
    from beanie.operators import In
    other_users_list = await models.User.find(
        In(models.User.id, [PydanticObjectId(uid) for uid in other_user_ids if PydanticObjectId.is_valid(uid)])
    ).to_list()
    other_users_map = {str(u.id): u for u in other_users_list}

    result = []
    for chat in chats:
        other_user_id = chat.other_user_id if str(chat.user_id) == str(current_user.id) else chat.user_id
        other_user = other_users_map.get(str(other_user_id))

        result.append({
            "id": str(chat.id),
            "other_user": {
                "id": str(other_user.id),
                "name": other_user.name,
                "avatar": other_user.avatar,
                "role": other_user.role
            },
            "last_message": chat.last_message,
            "last_message_time": chat.last_message_time,
            "unread_count": chat.unread_count if str(chat.user_id) == str(current_user.id) else 0,
            "product_id": chat.product_id
        })
    
    return result

@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str, current_user: models.User = Depends(get_current_user)):
    chat = await _get_chat_by_id(chat_id)
    if chat and str(chat.user_id) != str(current_user.id) and str(chat.other_user_id) != str(current_user.id):
        chat = None

    if not chat:
        raise HTTPException(status_code=404, detail=E.CHAT_NOT_FOUND)

    messages = await models.Message.find(
        models.Message.chat_id == chat_id
    ).sort("timestamp").to_list()

    return [_msg_dict(msg) for msg in messages]

@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: str,
    message_text: str,
    current_user: models.User = Depends(get_current_user)
):
    chat = await _get_chat_by_id(chat_id)
    if chat and str(chat.user_id) != str(current_user.id) and str(chat.other_user_id) != str(current_user.id):
        chat = None

    if not chat:
        raise HTTPException(status_code=404, detail=E.CHAT_NOT_FOUND)

    new_message = models.Message(
        chat_id=chat_id,
        sender_id=str(current_user.id),
        text=message_text,
        timestamp=datetime.utcnow()
    )
    await new_message.insert()
    
    chat.last_message = message_text
    chat.last_message_time = datetime.utcnow()
    
    if str(chat.user_id) != str(current_user.id):
        chat.unread_count += 1
    
    await chat.save()

    return _msg_dict(new_message)

@router.post("/chats/{chat_id}/mark-read")
async def mark_chat_as_read(chat_id: str, current_user: models.User = Depends(get_current_user)):
    chat = await _get_chat_by_id(chat_id)
    if chat and str(chat.user_id) != str(current_user.id):
        chat = None
    
    if not chat:
        raise HTTPException(status_code=404, detail=E.CHAT_PERMISSION_DENIED)
    
    old_count = chat.unread_count
    chat.unread_count = 0
    await chat.save()
    
    return {"message": "Chat marked as read", "previous_unread_count": old_count}

@router.post("/chats/")
async def create_chat(
    other_user_id: str,
    product_id: Optional[str] = None,
    initial_message: Optional[str] = None,
    current_user: models.User = Depends(get_current_user)
):
    existing_chat = await models.Chat.find_one(
        {"$or": [
            {"user_id": str(current_user.id), "other_user_id": other_user_id},
            {"user_id": other_user_id, "other_user_id": str(current_user.id)}
        ]}
    )
    
    if existing_chat:
        return {"chat_id": str(existing_chat.id), "existing": True}
    
    new_chat = models.Chat(
        user_id=str(current_user.id),
        other_user_id=other_user_id,
        product_id=product_id,
        last_message=initial_message or "",
        last_message_time=datetime.utcnow(),
        unread_count=0
    )
    await new_chat.insert()
    
    if initial_message:
        message = models.Message(
            chat_id=str(new_chat.id),
            sender_id=str(current_user.id),
            text=initial_message,
            timestamp=datetime.utcnow()
        )
        await message.insert()
    
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

    user = await models.User.find_one(models.User.phone_hash == phone)
    if not user:
        await websocket.close(code=4001)
        return

    # Verify the user belongs to this chat
    chat = await _get_chat_by_id(chat_id)
    if not chat or (str(chat.user_id) != str(user.id) and str(chat.other_user_id) != str(user.id)):
        await websocket.close(code=4003)
        return

    user_id = str(user.id)
    await chat_manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Basic message length guard
            if len(data) > 4000:
                continue
            try:
                new_message = models.Message(
                    chat_id=chat_id,
                    sender_id=user_id,
                    text=data,
                    timestamp=datetime.utcnow()
                )
                await new_message.insert()

                chat = await models.Chat.get(chat_id)
                if chat:
                    chat.last_message = data
                    chat.last_message_time = datetime.utcnow()
                    if str(chat.user_id) != user_id:
                        chat.unread_count += 1
                    await chat.save()
            except Exception as e:
                print(f"Error saving websocket message: {e}")

            await chat_manager.broadcast(chat_id, f"{user_id}:{data}", websocket)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_id, websocket)
