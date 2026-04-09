from fastapi import APIRouter, Depends
import os
import uuid

import models

from core.security import get_password_hash
from core.encryption import encrypt, hmac_hash
import telegram_bot

router = APIRouter(prefix="/dev", tags=["dev"])


async def _clear_collection(doc_class):
    await doc_class.find_all().delete()


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

@router.post("/reset-seed")
async def reset_and_seed():
    """Barcha test ma'lumotlarini o'chirib qayta seed qiladi."""
    for cls in [models.User, models.Category, models.Product,
                models.Order, models.Review, models.FraudReport]:
        await cls.find_all().delete()
    return await seed_data()


@router.post("/seed")
async def seed_data():
    if await models.User.find_one(models.User.phone_hash == hmac_hash("seller1")):
        return {"message": "Data already exists"}

    def make_user(**kw) -> models.User:
        phone = kw.pop("phone")
        tin   = kw.pop("tin", None)
        return models.User(
            phone=encrypt(phone),
            phone_hash=hmac_hash(phone),
            tin=encrypt(tin) if tin else None,
            **kw
        )

    # ── Kategoriyalar ───────────────────────────────────────────────────────
    cat_veg   = models.Category(name="Vegetables", icon="🥕")
    cat_fruit = models.Category(name="Fruit",      icon="🍎")
    cat_dairy = models.Category(name="Dairy",      icon="🥛")
    cat_grain = models.Category(name="Grain",      icon="🌾")
    cat_meat  = models.Category(name="Meat",       icon="🥩")
    for c in [cat_veg, cat_fruit, cat_dairy, cat_grain, cat_meat]:
        await c.insert()

    # ── Sotuvchilar ─────────────────────────────────────────────────────────
    seller1 = make_user(
        phone="seller1", hashed_password=get_password_hash("password"),
        role=models.UserRole.seller, name="Green Valley Farm",
        tin="123456789", is_online=True, rating=4.8, review_count=3,
        description="Toshkent viloyatidagi organik ferma. 10 yillik tajriba.",
    )
    seller2 = make_user(
        phone="seller2", hashed_password=get_password_hash("password"),
        role=models.UserRole.seller, name="Samarqand Bog'i",
        tin=None, is_online=False, rating=3.5, review_count=2,
        description="Samarqand mevalaridagi fermer xo'jaligi.",
    )
    seller3 = make_user(
        phone="seller3", hashed_password=get_password_hash("password"),
        role=models.UserRole.seller, name="Fergana Sut Zavodi",
        tin="987654321", is_online=True, rating=4.6, review_count=4,
        description="Farg'ona vodiysida 15 yillik sut mahsulotlari ishlab chiqarish.",
    )
    seller4 = make_user(
        phone="seller4", hashed_password=get_password_hash("password"),
        role=models.UserRole.seller, name="Andijon Donchisi",
        tin="112233445", is_online=False, rating=4.2, review_count=2,
        description="Don mahsulotlari va un. Katta hajmda yetkazib berish.",
    )
    seller5 = make_user(
        phone="seller5", hashed_password=get_password_hash("password"),
        role=models.UserRole.seller, name="Go'sht Bozori Pro",
        tin=None, is_online=True, rating=2.9, review_count=2,
        description="Yangi go'sht mahsulotlari. Toshkent bo'yicha yetkazib berish.",
    )
    for s in [seller1, seller2, seller3, seller4, seller5]:
        await s.insert()

    # ── Xaridorlar ──────────────────────────────────────────────────────────
    buyer1 = make_user(phone="buyer1", hashed_password=get_password_hash("password"),
                       role=models.UserRole.buyer, name="Alisher Karimov")
    buyer2 = make_user(phone="buyer2", hashed_password=get_password_hash("password"),
                       role=models.UserRole.buyer, name="Malika Yusupova")
    buyer3 = make_user(phone="buyer3", hashed_password=get_password_hash("password"),
                       role=models.UserRole.buyer, name="Jasur Toshmatov")
    for b in [buyer1, buyer2, buyer3]:
        await b.insert()

    # ── Mahsulotlar ─────────────────────────────────────────────────────────
    products_data = [
        # seller1 — sabzavot
        dict(seller_id=str(seller1.id), category_id=str(cat_veg.id),
             name="Organik Pomidor", price=4.99, unit="kg",
             image="https://images.unsplash.com/photo-1546470427-227e99f9a46e?w=800",
             description="Toza organik pomidor. Kimyosiz, ferma mahsuloti.",
             rating=4.8, review_count=3, views=210, sales=85),
        dict(seller_id=str(seller1.id), category_id=str(cat_veg.id),
             name="Bodring (toza)", price=2.50, unit="kg",
             image="https://images.unsplash.com/photo-1568584711271-6c929fb49b60?w=800",
             description="Issiqxonada yetishtirilgan bodring. Har kuni yangi.",
             rating=4.6, review_count=2, views=140, sales=60),
        dict(seller_id=str(seller1.id), category_id=str(cat_veg.id),
             name="Qizil Qalampir", price=5.50, unit="kg",
             image="https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=800",
             description="Mazali va vitaminga boy qizil qalampir.",
             rating=4.7, review_count=1, views=90, sales=35),
        # seller2 — meva
        dict(seller_id=str(seller2.id), category_id=str(cat_fruit.id),
             name="Samarqand Olma", price=3.20, unit="kg",
             image="https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=800",
             description="Samarqandning mashhur mahalliy olmasi. Shirin va xushbo'y.",
             rating=3.5, review_count=2, views=100, sales=38),
        dict(seller_id=str(seller2.id), category_id=str(cat_fruit.id),
             name="Uzum (Toʻytepa)", price=6.80, unit="kg",
             image="https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=800",
             description="To'ytepa toʻq qizil uзими. Juda shirin.",
             rating=3.8, review_count=1, views=75, sales=22),
        # seller3 — sut
        dict(seller_id=str(seller3.id), category_id=str(cat_dairy.id),
             name="Tabiiy Qatiq", price=3.50, unit="litr",
             image="https://images.unsplash.com/photo-1563636619-e9143da7973b?w=800",
             description="Tabiiy sigir sutidan tayyorlangan qalin qatiq.",
             rating=4.9, review_count=4, views=180, sales=95),
        dict(seller_id=str(seller3.id), category_id=str(cat_dairy.id),
             name="Pishloq (Suluguni)", price=12.00, unit="kg",
             image="https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=800",
             description="Farg'ona usulida tayyorlangan suluguni pishloq.",
             rating=4.5, review_count=2, views=120, sales=48),
        # seller4 — don
        dict(seller_id=str(seller4.id), category_id=str(cat_grain.id),
             name="Bug'doy Uni (1-nav)", price=1.20, unit="kg",
             image="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800",
             description="Toza 1-nav bug'doy uni. Non pishirish uchun ideal.",
             rating=4.3, review_count=2, views=160, sales=200),
        dict(seller_id=str(seller4.id), category_id=str(cat_grain.id),
             name="Guruch (Devzira)", price=4.50, unit="kg",
             image="https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800",
             description="Haqiqiy Qo'qon devzira guruchi. Osh uchun eng yaxshisi.",
             rating=4.1, review_count=1, views=130, sales=110),
        # seller5 — go'sht
        dict(seller_id=str(seller5.id), category_id=str(cat_meat.id),
             name="Mol Go'shti", price=15.00, unit="kg",
             image="https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=800",
             description="Yangi mol go'shti. Bugun so'yilgan.",
             rating=3.0, review_count=2, views=85, sales=30),
        dict(seller_id=str(seller5.id), category_id=str(cat_meat.id),
             name="Qo'y Go'shti", price=18.00, unit="kg",
             image="https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=800",
             description="Tog' qo'yining go'shti. Toza va yog'li.",
             rating=2.8, review_count=1, views=60, sales=15),
    ]
    prods = []
    for d in products_data:
        p = models.Product(**d)
        await p.insert()
        prods.append(p)

    # mahsulotni nomi bo'yicha tezda topish uchun
    def prod(name):
        return next(p for p in prods if p.name == name)

    # ── Buyurtmalar ─────────────────────────────────────────────────────────
    orders_data = [
        # buyer1 — seller1 bilan (completed x2, cancelled x1)
        dict(buyer=buyer1, seller=seller1, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Organik Pomidor"), 3), (prod("Bodring (toza)"), 2)]),
        dict(buyer=buyer1, seller=seller1, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.pickup,
             items=[(prod("Qizil Qalampir"), 1)]),
        dict(buyer=buyer1, seller=seller1, status=models.OrderStatus.cancelled,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Organik Pomidor"), 5)]),
        # buyer1 — seller2
        dict(buyer=buyer1, seller=seller2, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Samarqand Olma"), 4)]),
        dict(buyer=buyer1, seller=seller2, status=models.OrderStatus.cancelled,
             delivery=models.DeliveryMethod.pickup,
             items=[(prod("Uzum (Toʻytepa)"), 2)]),
        # buyer2 — seller3
        dict(buyer=buyer2, seller=seller3, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Tabiiy Qatiq"), 5), (prod("Pishloq (Suluguni)"), 1)]),
        dict(buyer=buyer2, seller=seller3, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.pickup,
             items=[(prod("Tabiiy Qatiq"), 3)]),
        dict(buyer=buyer2, seller=seller3, status=models.OrderStatus.in_process,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Pishloq (Suluguni)"), 2)]),
        # buyer2 — seller4
        dict(buyer=buyer2, seller=seller4, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.pickup,
             items=[(prod("Bug'doy Uni (1-nav)"), 20), (prod("Guruch (Devzira)"), 5)]),
        dict(buyer=buyer2, seller=seller4, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Guruch (Devzira)"), 3)]),
        # buyer3 — seller5
        dict(buyer=buyer3, seller=seller5, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Mol Go'shti"), 2)]),
        dict(buyer=buyer3, seller=seller5, status=models.OrderStatus.cancelled,
             delivery=models.DeliveryMethod.pickup,
             items=[(prod("Qo'y Go'shti"), 1)]),
        # buyer3 — seller1
        dict(buyer=buyer3, seller=seller1, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(prod("Organik Pomidor"), 2)]),
    ]
    db_orders = []
    for od in orders_data:
        total = sum(p.price * q for p, q in od["items"])
        o = models.Order(
            buyer_id=str(od["buyer"].id), seller_id=str(od["seller"].id),
            status=od["status"], total=total, delivery_method=od["delivery"],
            items=[models.OrderItem(product_id=str(p.id), quantity=q, price_at_purchase=p.price)
                   for p, q in od["items"]]
        )
        await o.insert()
        db_orders.append(o)

    # ── Sharhlar ─────────────────────────────────────────────────────────────
    reviews_data = [
        # seller1 sharhlar
        dict(reviewer=buyer1, seller=seller1, order=db_orders[0],
             product=prod("Organik Pomidor"), rating=5,
             comment="Pomidorlar juda yangi va mazali! Qo'shni xonadonga ham tavsiya qildim."),
        dict(reviewer=buyer1, seller=seller1, order=db_orders[1],
             product=prod("Qizil Qalampir"), rating=4,
             comment="Qalampir yaxshi, lekin bir nechtasi biroz ezilgan edi. Umuman mamnunam."),
        dict(reviewer=buyer3, seller=seller1, order=db_orders[12],
             product=prod("Organik Pomidor"), rating=5,
             comment="Eng yaxshi pomidor! Har hafta buyurtma beraman."),
        # seller2 sharhlar
        dict(reviewer=buyer1, seller=seller2, order=db_orders[3],
             product=prod("Samarqand Olma"), rating=3,
             comment="Olma shirin, lekin yetkazib berish kech bo'ldi. Keyingi safar tezroq bo'lsin."),
        dict(reviewer=buyer1, seller=seller2, order=db_orders[3],  # unique order suffix
             product=prod("Samarqand Olma"), rating=4,
             comment="Sifat yaxshi, narx ham mos. Yana buyurtma beraman."),
        # seller3 sharhlar
        dict(reviewer=buyer2, seller=seller3, order=db_orders[5],
             product=prod("Tabiiy Qatiq"), rating=5,
             comment="Eng yaxshi qatiq! Do'konnikidan ming marta yaxshi. Har kuni olamiz."),
        dict(reviewer=buyer2, seller=seller3, order=db_orders[6],
             product=prod("Tabiiy Qatiq"), rating=5,
             comment="Sifat doimo yuqori. Ishonchli sotuvchi."),
        dict(reviewer=buyer2, seller=seller3, order=db_orders[5],
             product=prod("Pishloq (Suluguni)"), rating=4,
             comment="Pishloq juda mazali, lekin narxi biroz qimmat."),
        dict(reviewer=buyer2, seller=seller3, order=db_orders[8],
             product=prod("Guruch (Devzira)"), rating=4,
             comment="Devzira guruch ajoyib! Osh juda mazali chiqdi."),
        # seller4 sharhlar
        dict(reviewer=buyer2, seller=seller4, order=db_orders[8],
             product=prod("Bug'doy Uni (1-nav)"), rating=4,
             comment="Un sifati yaxshi, narxi ham qo'lbola. Yana olaman."),
        dict(reviewer=buyer2, seller=seller4, order=db_orders[9],
             product=prod("Guruch (Devzira)"), rating=4,
             comment="Guruch to'liq va sifatli. Yetkazib berish ham o'z vaqtida."),
        # seller5 sharhlar
        dict(reviewer=buyer3, seller=seller5, order=db_orders[10],
             product=prod("Mol Go'shti"), rating=3,
             comment="Go'sht yaxshi, lekin yetkazib berish kech keldi va qadoqlash yomon edi."),
        dict(reviewer=buyer3, seller=seller5, order=db_orders[10],
             product=prod("Mol Go'shti"), rating=3,
             comment="O'rtacha sifat. Narxga yarasha deyish mumkin."),
    ]

    review_count = 0
    used_order_ids = set()
    for i, rd in enumerate(reviews_data):
        oid = str(rd["order"].id)
        # unique key uchun index ishlatamiz
        unique_oid = oid if oid not in used_order_ids else f"{oid}_{i}"
        used_order_ids.add(unique_oid)
        r = models.Review(
            reviewer_id=str(rd["reviewer"].id),
            seller_id=str(rd["seller"].id),
            order_id=unique_oid,
            product_id=str(rd["product"].id),
            rating=rd["rating"],
            comment=rd["comment"],
            is_verified_purchase=True,
        )
        await r.insert()
        review_count += 1

    return {
        "message": "Seed data inserted",
        "accounts": {
            "sellers": ["seller1..seller5 / password"],
            "buyers":  ["buyer1..buyer3 / password"],
        },
        "categories": 5,
        "products": len(prods),
        "orders": len(db_orders),
        "reviews": review_count,
    }


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

    # Neo4j holati
    neo4j_status = neo4j_db.is_available()
    neo4j_nodes = {}
    if neo4j_status:
        user_count    = neo4j_db.execute_query("MATCH (u:User)    RETURN count(u) AS n")
        product_count = neo4j_db.execute_query("MATCH (p:Product) RETURN count(p) AS n")
        edge_count    = neo4j_db.execute_query("MATCH ()-[r:INTERACTED]->() RETURN count(r) AS n")
        neo4j_nodes = {
            "users":        user_count[0]["n"]    if user_count    else 0,
            "products":     product_count[0]["n"] if product_count else 0,
            "interactions": edge_count[0]["n"]    if edge_count    else 0,
        }

    # MongoDB interactions
    interactions = await models.ProductInteraction.find_all().to_list()
    total_interactions = len(interactions)
    unique_users    = len({i.user_id    for i in interactions})
    unique_products = len({i.product_id for i in interactions})

    # SVD explained variance
    svd_variance = None
    svd_components = None
    if total_interactions >= 5 and unique_users >= 2 and unique_products >= 2:
        _WEIGHTS = {"purchase": 3, "click": 2, "view": 1}
        user_ids    = list({i.user_id    for i in interactions})
        product_ids = list({i.product_id for i in interactions})
        user_enc = {uid: idx for idx, uid in enumerate(user_ids)}
        prod_enc = {pid: idx for idx, pid in enumerate(product_ids)}

        matrix = np.zeros((len(user_ids), len(product_ids)), dtype=np.float32)
        for inter in interactions:
            ui = user_enc.get(inter.user_id)
            pi = prod_enc.get(inter.product_id)
            if ui is not None and pi is not None:
                w = _WEIGHTS.get(inter.interaction_type.value, 1)
                matrix[ui, pi] = max(matrix[ui, pi], w)

        n_components = min(10, unique_users - 1, unique_products - 1)
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        svd.fit_transform(matrix)
        svd_variance   = round(float(svd.explained_variance_ratio_.sum()), 4)
        svd_components = n_components

    return {
        "neo4j": {
            "available": neo4j_status,
            "nodes": neo4j_nodes,
        },
        "mongodb_interactions": {
            "total":            total_interactions,
            "unique_users":     unique_users,
            "unique_products":  unique_products,
        },
        "svd_model": {
            "status":              "trained" if svd_variance is not None else "insufficient_data",
            "explained_variance":  svd_variance,
            "n_components":        svd_components,
            "note": (
                "0.7+ = yaxshi, 0.5-0.7 = qoniqarli, <0.5 = ko'proq ma'lumot kerak"
                if svd_variance is not None else
                f"Kamida 5 ta interaksiya kerak (hozir: {total_interactions})"
            ),
        },
        "recommendation_pipeline": [
            "1. SVD Matrix Factorization (sklearn) — asosiy",
            "2. Neo4j Collaborative Filtering       — agar Neo4j ishlasa",
            "3. MongoDB top-by-views                — fallback",
        ],
    }
