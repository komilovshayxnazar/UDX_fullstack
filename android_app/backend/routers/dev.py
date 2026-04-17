"""
routers/dev.py — Faqat development/debug endpointlari.

Mock ma'lumotlar: mock_data/seed.py
Bu router production deploymentda o'chirilishi kerak
(masalan, ENVIRONMENT != "development" bo'lsa include qilinmasin).
"""

from fastapi import APIRouter
import os

import models
from core.encryption import hmac_hash
from mock_data.seed import run_seed
import telegram_bot

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/telegram/status")
async def telegram_status(username: str = ""):
    """Bot holati va username /start yuborganmi tekshiradi."""
    token_set  = bool(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    bot_running = telegram_bot._app is not None
    chat_id     = telegram_bot.get_chat_id(username) if username else None
    return {
        "token_configured":    token_set,
        "bot_running":         bot_running,
        "username_registered": chat_id is not None,
        "chat_id":             chat_id,
    }


@router.post("/seed")
async def seed_data():
    """Mock ma'lumotlarni bazaga yozadi (agar mavjud bo'lmasa)."""
    return await run_seed()


@router.post("/reset-seed")
async def reset_and_seed():
    """Barcha test ma'lumotlarini o'chirib qayta seed qiladi."""
    for cls in [models.User, models.Category, models.Product,
                models.Order, models.Review, models.FraudReport]:
        await cls.find_all().delete()
    return await run_seed()


@router.post("/sync-categories")
async def sync_categories():
    """Bazada yo'q kategoriyalarni qo'shadi (mavjudlarini o'zgartirmaydi)."""
    from mock_data.seed import CATEGORIES
    added = []
    for cat in CATEGORIES:
        exists = await models.Category.find_one({"name": cat["name"]})
        if not exists:
            await models.Category(**cat).insert()
            added.append(cat["name"])
    return {"added": added, "total": await models.Category.count()}


@router.post("/orders/{order_id}/complete")
async def dev_complete_order(order_id: str):
    """Test uchun — order statusini completed ga o'zgartiradi."""
    from fastapi import HTTPException
    order = await models.Order.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = models.OrderStatus.completed
    await order.save()
    return {"status": "completed", "order_id": order_id}


@router.get("/ml-stats")
async def ml_stats():
    """
    ML model diagnostikasi:
    - Neo4j holati
    - Interaction ma'lumotlar soni
    - SVD explained variance (model 'aniqligi')
    """
    import numpy as np
    from sklearn.decomposition import TruncatedSVD
    from core import neo4j_db

    neo4j_status = neo4j_db.is_available()
    neo4j_nodes  = {}
    if neo4j_status:
        u = neo4j_db.execute_query("MATCH (u:User)    RETURN count(u) AS n")
        p = neo4j_db.execute_query("MATCH (p:Product) RETURN count(p) AS n")
        e = neo4j_db.execute_query("MATCH ()-[r:INTERACTED]->() RETURN count(r) AS n")
        neo4j_nodes = {
            "users":        u[0]["n"] if u else 0,
            "products":     p[0]["n"] if p else 0,
            "interactions": e[0]["n"] if e else 0,
        }

    interactions    = await models.ProductInteraction.find_all().to_list()
    total           = len(interactions)
    unique_users    = len({i.user_id    for i in interactions})
    unique_products = len({i.product_id for i in interactions})

    svd_variance   = None
    svd_components = None
    if total >= 5 and unique_users >= 2 and unique_products >= 2:
        _W       = {"purchase": 3, "click": 2, "view": 1}
        user_ids = list({i.user_id    for i in interactions})
        prod_ids = list({i.product_id for i in interactions})
        u_enc    = {uid: idx for idx, uid in enumerate(user_ids)}
        p_enc    = {pid: idx for idx, pid in enumerate(prod_ids)}

        matrix = np.zeros((len(user_ids), len(prod_ids)), dtype=np.float32)
        for inter in interactions:
            ui = u_enc.get(inter.user_id)
            pi = p_enc.get(inter.product_id)
            if ui is not None and pi is not None:
                matrix[ui, pi] = max(matrix[ui, pi], _W.get(inter.interaction_type.value, 1))

        n   = min(10, unique_users - 1, unique_products - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        svd.fit_transform(matrix)
        svd_variance   = round(float(svd.explained_variance_ratio_.sum()), 4)
        svd_components = n

    return {
        "neo4j": {"available": neo4j_status, "nodes": neo4j_nodes},
        "mongodb_interactions": {
            "total":           total,
            "unique_users":    unique_users,
            "unique_products": unique_products,
        },
        "svd_model": {
            "status":             "trained" if svd_variance is not None else "insufficient_data",
            "explained_variance": svd_variance,
            "n_components":       svd_components,
            "note": (
                "0.7+ = yaxshi, 0.5-0.7 = qoniqarli, <0.5 = ko'proq ma'lumot kerak"
                if svd_variance is not None else
                f"Kamida 5 ta interaksiya kerak (hozir: {total})"
            ),
        },
        "recommendation_pipeline": [
            "1. SVD Matrix Factorization (sklearn) — asosiy",
            "2. Neo4j Collaborative Filtering       — agar Neo4j ishlasa",
            "3. MongoDB top-by-views                — fallback",
        ],
    }
