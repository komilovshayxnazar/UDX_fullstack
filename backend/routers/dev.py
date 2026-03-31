from fastapi import APIRouter, Depends
import os
import uuid

import models

from core.security import get_password_hash
import telegram_bot

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/telegram/status")
async def telegram_status(username: str = ""):
    """Debug endpoint: check bot status and whether a username has sent /start."""
    token_set = bool(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    bot_running = telegram_bot._app is not None   # read live module attribute
    chat_id = telegram_bot.get_chat_id(username) if username else None
    return {
        "token_configured": token_set,
        "bot_running": bot_running,
        "username_registered": chat_id is not None,
        "chat_id": chat_id,
    }

@router.post("/seed")
async def seed_data():
    if not await models.User.find_one(models.User.phone == "seller1"):
        seller = models.User(
            phone="seller1",
            hashed_password=get_password_hash("password"),
            role=models.UserRole.seller,
            name="Green Valley Farm",
            rating=4.8
        )
        await seller.insert()
        
        cat = models.Category(name="vegetables", icon="🥕")
        await cat.insert()
        
        prod = models.Product(
            seller_id=str(seller.id),
            category_id=str(cat.id),
            name="Organic Tomatoes",
            price=4.99,
            unit="kg",
            image="https://images.unsplash.com/photo-1546470427-227e99f9a46e?w=800",
            description="Fresh organic tomatoes",
            rating=4.8,
            review_count=45
        )
        await prod.insert()
        return {"message": "Data seeded"}
    return {"message": "Data already exists"}
