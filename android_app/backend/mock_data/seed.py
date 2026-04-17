"""
mock_data/seed.py — Test ma'lumotlari (faqat development uchun).

Bu fayl ishlab chiqarish (production) kodiga hech qachon import qilinmasin.
Faqat routers/dev.py orqali chaqiriladi.
"""

import models
from core.security import get_password_hash
from core.encryption import encrypt, hmac_hash


# ── Yordamchi funksiya ────────────────────────────────────────────────────────

def make_user(**kw) -> models.User:
    """Telefon va TINni shifrlagan holda User obyekti yaratadi."""
    phone = kw.pop("phone")
    tin   = kw.pop("tin", None)
    return models.User(
        phone=encrypt(phone),
        phone_hash=hmac_hash(phone),
        tin=encrypt(tin) if tin else None,
        **kw
    )


# ── Kategoriyalar ─────────────────────────────────────────────────────────────

CATEGORIES = [
    {"name": "Vegetables",   "icon": "🥕"},
    {"name": "Fruit",        "icon": "🍎"},
    {"name": "Dairy",        "icon": "🥛"},
    {"name": "Grain",        "icon": "🌾"},
    {"name": "Meat",         "icon": "🥩"},
    {"name": "Greens",       "icon": "🥬"},
    {"name": "B2B Market",   "icon": "🏭"},
    {"name": "Machinery",    "icon": "🚜"},
    {"name": "Fertilizers",  "icon": "🧪"},
    {"name": "Tools",        "icon": "🔧"},
    {"name": "Organic",      "icon": "🌿"},
    {"name": "Seeds",        "icon": "🌱"},
]


# ── Foydalanuvchilar ──────────────────────────────────────────────────────────

SELLERS = [
    dict(phone="seller1", hashed_password=get_password_hash("password"),
         role=models.UserRole.seller, name="Green Valley Farm",
         tin="123456789", is_online=True, rating=4.8, review_count=3,
         description="Toshkent viloyatidagi organik ferma. 10 yillik tajriba."),
    dict(phone="seller2", hashed_password=get_password_hash("password"),
         role=models.UserRole.seller, name="Samarqand Bog'i",
         tin=None, is_online=False, rating=3.5, review_count=2,
         description="Samarqand mevalaridagi fermer xo'jaligi."),
    dict(phone="seller3", hashed_password=get_password_hash("password"),
         role=models.UserRole.seller, name="Fergana Sut Zavodi",
         tin="987654321", is_online=True, rating=4.6, review_count=4,
         description="Farg'ona vodiysida 15 yillik sut mahsulotlari ishlab chiqarish."),
    dict(phone="seller4", hashed_password=get_password_hash("password"),
         role=models.UserRole.seller, name="Andijon Donchisi",
         tin="112233445", is_online=False, rating=4.2, review_count=2,
         description="Don mahsulotlari va un. Katta hajmda yetkazib berish."),
    dict(phone="seller5", hashed_password=get_password_hash("password"),
         role=models.UserRole.seller, name="Go'sht Bozori Pro",
         tin=None, is_online=True, rating=2.9, review_count=2,
         description="Yangi go'sht mahsulotlari. Toshkent bo'yicha yetkazib berish."),
]

BUYERS = [
    dict(phone="buyer1", hashed_password=get_password_hash("password"),
         role=models.UserRole.buyer, name="Alisher Karimov"),
    dict(phone="buyer2", hashed_password=get_password_hash("password"),
         role=models.UserRole.buyer, name="Malika Yusupova"),
    dict(phone="buyer3", hashed_password=get_password_hash("password"),
         role=models.UserRole.buyer, name="Jasur Toshmatov"),
]


# ── Mahsulotlar (seller_id va category_id keyinroq to'ldiriladi) ─────────────

def build_products(sellers: list, cats: dict) -> list[dict]:
    """
    sellers: [seller1, seller2, ...] (insert qilingan User obyektlari)
    cats: {"Vegetables": Category, "Fruit": Category, ...}
    """
    s1, s2, s3, s4, s5 = sellers
    veg, fruit, dairy, grain, meat = (
        cats["Vegetables"], cats["Fruit"],
        cats["Dairy"], cats["Grain"], cats["Meat"],
    )
    return [
        # seller1 — sabzavot
        dict(seller_id=str(s1.id), category_id=str(veg.id),
             name="Organik Pomidor", price=4.99, unit="kg",
             image="https://images.unsplash.com/photo-1546470427-227e99f9a46e?w=800",
             description="Toza organik pomidor. Kimyosiz, ferma mahsuloti.",
             rating=4.8, review_count=3, views=210, sales=85),
        dict(seller_id=str(s1.id), category_id=str(veg.id),
             name="Bodring (toza)", price=2.50, unit="kg",
             image="https://images.unsplash.com/photo-1568584711271-6c929fb49b60?w=800",
             description="Issiqxonada yetishtirilgan bodring. Har kuni yangi.",
             rating=4.6, review_count=2, views=140, sales=60),
        dict(seller_id=str(s1.id), category_id=str(veg.id),
             name="Qizil Qalampir", price=5.50, unit="kg",
             image="https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=800",
             description="Mazali va vitaminga boy qizil qalampir.",
             rating=4.7, review_count=1, views=90, sales=35),
        # seller2 — meva
        dict(seller_id=str(s2.id), category_id=str(fruit.id),
             name="Samarqand Olma", price=3.20, unit="kg",
             image="https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=800",
             description="Samarqandning mashhur mahalliy olmasi. Shirin va xushbo'y.",
             rating=3.5, review_count=2, views=100, sales=38),
        dict(seller_id=str(s2.id), category_id=str(fruit.id),
             name="Uzum (Toʻytepa)", price=6.80, unit="kg",
             image="https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=800",
             description="To'ytepa toʻq qizil uzumi. Juda shirin.",
             rating=3.8, review_count=1, views=75, sales=22),
        # seller3 — sut
        dict(seller_id=str(s3.id), category_id=str(dairy.id),
             name="Tabiiy Qatiq", price=3.50, unit="litr",
             image="https://images.unsplash.com/photo-1563636619-e9143da7973b?w=800",
             description="Tabiiy sigir sutidan tayyorlangan qalin qatiq.",
             rating=4.9, review_count=4, views=180, sales=95),
        dict(seller_id=str(s3.id), category_id=str(dairy.id),
             name="Pishloq (Suluguni)", price=12.00, unit="kg",
             image="https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=800",
             description="Farg'ona usulida tayyorlangan suluguni pishloq.",
             rating=4.5, review_count=2, views=120, sales=48),
        # seller4 — don
        dict(seller_id=str(s4.id), category_id=str(grain.id),
             name="Bug'doy Uni (1-nav)", price=1.20, unit="kg",
             image="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800",
             description="Toza 1-nav bug'doy uni. Non pishirish uchun ideal.",
             rating=4.3, review_count=2, views=160, sales=200),
        dict(seller_id=str(s4.id), category_id=str(grain.id),
             name="Guruch (Devzira)", price=4.50, unit="kg",
             image="https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800",
             description="Haqiqiy Qo'qon devzira guruchi. Osh uchun eng yaxshisi.",
             rating=4.1, review_count=1, views=130, sales=110),
        # seller5 — go'sht
        dict(seller_id=str(s5.id), category_id=str(meat.id),
             name="Mol Go'shti", price=15.00, unit="kg",
             image="https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=800",
             description="Yangi mol go'shti. Bugun so'yilgan.",
             rating=3.0, review_count=2, views=85, sales=30),
        dict(seller_id=str(s5.id), category_id=str(meat.id),
             name="Qo'y Go'shti", price=18.00, unit="kg",
             image="https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=800",
             description="Tog' qo'yining go'shti. Toza va yog'li.",
             rating=2.8, review_count=1, views=60, sales=15),
    ]


# ── Buyurtmalar ───────────────────────────────────────────────────────────────

def build_orders(buyers: list, sellers: list, prods: list) -> list[dict]:
    """
    buyers:  [buyer1, buyer2, buyer3]
    sellers: [seller1, ..., seller5]
    prods:   insert qilingan Product obyektlari ro'yxati
    """
    b1, b2, b3 = buyers
    s1, s2, s3, s4, s5 = sellers

    def p(name):
        return next(x for x in prods if x.name == name)

    return [
        # buyer1 — seller1
        dict(buyer=b1, seller=s1, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Organik Pomidor"), 3), (p("Bodring (toza)"), 2)]),
        dict(buyer=b1, seller=s1, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.pickup,
             items=[(p("Qizil Qalampir"), 1)]),
        dict(buyer=b1, seller=s1, status=models.OrderStatus.cancelled,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Organik Pomidor"), 5)]),
        # buyer1 — seller2
        dict(buyer=b1, seller=s2, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Samarqand Olma"), 4)]),
        dict(buyer=b1, seller=s2, status=models.OrderStatus.cancelled,
             delivery=models.DeliveryMethod.pickup,
             items=[(p("Uzum (Toʻytepa)"), 2)]),
        # buyer2 — seller3
        dict(buyer=b2, seller=s3, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Tabiiy Qatiq"), 5), (p("Pishloq (Suluguni)"), 1)]),
        dict(buyer=b2, seller=s3, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.pickup,
             items=[(p("Tabiiy Qatiq"), 3)]),
        dict(buyer=b2, seller=s3, status=models.OrderStatus.in_process,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Pishloq (Suluguni)"), 2)]),
        # buyer2 — seller4
        dict(buyer=b2, seller=s4, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.pickup,
             items=[(p("Bug'doy Uni (1-nav)"), 20), (p("Guruch (Devzira)"), 5)]),
        dict(buyer=b2, seller=s4, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Guruch (Devzira)"), 3)]),
        # buyer3 — seller5
        dict(buyer=b3, seller=s5, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Mol Go'shti"), 2)]),
        dict(buyer=b3, seller=s5, status=models.OrderStatus.cancelled,
             delivery=models.DeliveryMethod.pickup,
             items=[(p("Qo'y Go'shti"), 1)]),
        # buyer3 — seller1
        dict(buyer=b3, seller=s1, status=models.OrderStatus.completed,
             delivery=models.DeliveryMethod.courier,
             items=[(p("Organik Pomidor"), 2)]),
    ]


# ── Sharhlar ──────────────────────────────────────────────────────────────────

def build_reviews(buyers: list, sellers: list, prods: list, orders: list) -> list[dict]:
    b1, b2, b3 = buyers
    s1, s2, s3, s4, s5 = sellers

    def p(name):
        return next(x for x in prods if x.name == name)

    return [
        # seller1
        dict(reviewer=b1, seller=s1, order=orders[0],
             product=p("Organik Pomidor"), rating=5,
             comment="Pomidorlar juda yangi va mazali! Qo'shni xonadonga ham tavsiya qildim."),
        dict(reviewer=b1, seller=s1, order=orders[1],
             product=p("Qizil Qalampir"), rating=4,
             comment="Qalampir yaxshi, lekin bir nechtasi biroz ezilgan edi. Umuman mamnunam."),
        dict(reviewer=b3, seller=s1, order=orders[12],
             product=p("Organik Pomidor"), rating=5,
             comment="Eng yaxshi pomidor! Har hafta buyurtma beraman."),
        # seller2
        dict(reviewer=b1, seller=s2, order=orders[3],
             product=p("Samarqand Olma"), rating=3,
             comment="Olma shirin, lekin yetkazib berish kech bo'ldi. Keyingi safar tezroq bo'lsin."),
        dict(reviewer=b1, seller=s2, order=orders[3],
             product=p("Samarqand Olma"), rating=4,
             comment="Sifat yaxshi, narx ham mos. Yana buyurtma beraman."),
        # seller3
        dict(reviewer=b2, seller=s3, order=orders[5],
             product=p("Tabiiy Qatiq"), rating=5,
             comment="Eng yaxshi qatiq! Do'konnikidan ming marta yaxshi. Har kuni olamiz."),
        dict(reviewer=b2, seller=s3, order=orders[6],
             product=p("Tabiiy Qatiq"), rating=5,
             comment="Sifat doimo yuqori. Ishonchli sotuvchi."),
        dict(reviewer=b2, seller=s3, order=orders[5],
             product=p("Pishloq (Suluguni)"), rating=4,
             comment="Pishloq juda mazali, lekin narxi biroz qimmat."),
        dict(reviewer=b2, seller=s3, order=orders[8],
             product=p("Guruch (Devzira)"), rating=4,
             comment="Devzira guruch ajoyib! Osh juda mazali chiqdi."),
        # seller4
        dict(reviewer=b2, seller=s4, order=orders[8],
             product=p("Bug'doy Uni (1-nav)"), rating=4,
             comment="Un sifati yaxshi, narxi ham qo'lbola. Yana olaman."),
        dict(reviewer=b2, seller=s4, order=orders[9],
             product=p("Guruch (Devzira)"), rating=4,
             comment="Guruch to'liq va sifatli. Yetkazib berish ham o'z vaqtida."),
        # seller5
        dict(reviewer=b3, seller=s5, order=orders[10],
             product=p("Mol Go'shti"), rating=3,
             comment="Go'sht yaxshi, lekin yetkazib berish kech keldi va qadoqlash yomon edi."),
        dict(reviewer=b3, seller=s5, order=orders[10],
             product=p("Mol Go'shti"), rating=3,
             comment="O'rtacha sifat. Narxga yarasha deyish mumkin."),
    ]


# ── Asosiy seed funksiyasi ────────────────────────────────────────────────────

async def run_seed() -> dict:
    """
    Barcha mock ma'lumotlarni bazaga yozadi.
    Agar allaqachon yozilgan bo'lsa, hech narsa qilmaydi.
    """
    if await models.User.find_one(models.User.phone_hash == hmac_hash("seller1")):
        return {"message": "Data already exists"}

    # 1. Kategoriyalar
    cat_objects = []
    cat_by_name = {}
    for c in CATEGORIES:
        obj = models.Category(**c)
        await obj.insert()
        cat_objects.append(obj)
        cat_by_name[c["name"]] = obj

    # 2. Sotuvchilar
    seller_objects = []
    for s in SELLERS:
        obj = make_user(**s)
        await obj.insert()
        seller_objects.append(obj)

    # 3. Xaridorlar
    buyer_objects = []
    for b in BUYERS:
        obj = make_user(**b)
        await obj.insert()
        buyer_objects.append(obj)

    # 4. Mahsulotlar
    prod_objects = []
    for d in build_products(seller_objects, cat_by_name):
        obj = models.Product(**d)
        await obj.insert()
        prod_objects.append(obj)

    # 5. Buyurtmalar
    order_objects = []
    for od in build_orders(buyer_objects, seller_objects, prod_objects):
        total = sum(pr.price * q for pr, q in od["items"])
        obj = models.Order(
            buyer_id=str(od["buyer"].id),
            seller_id=str(od["seller"].id),
            status=od["status"],
            total=total,
            delivery_method=od["delivery"],
            items=[
                models.OrderItem(
                    product_id=str(pr.id),
                    quantity=q,
                    price_at_purchase=pr.price,
                )
                for pr, q in od["items"]
            ],
        )
        await obj.insert()
        order_objects.append(obj)

    # 6. Sharhlar
    review_count = 0
    used_order_ids: set[str] = set()
    for i, rd in enumerate(build_reviews(buyer_objects, seller_objects, prod_objects, order_objects)):
        oid = str(rd["order"].id)
        unique_oid = oid if oid not in used_order_ids else f"{oid}_{i}"
        used_order_ids.add(unique_oid)
        obj = models.Review(
            reviewer_id=str(rd["reviewer"].id),
            seller_id=str(rd["seller"].id),
            order_id=unique_oid,
            product_id=str(rd["product"].id),
            rating=rd["rating"],
            comment=rd["comment"],
            is_verified_purchase=True,
        )
        await obj.insert()
        review_count += 1

    return {
        "message": "Seed data inserted",
        "accounts": {
            "sellers": ["seller1..seller5 / password"],
            "buyers":  ["buyer1..buyer3 / password"],
        },
        "categories": len(cat_objects),
        "products":   len(prod_objects),
        "orders":     len(order_objects),
        "reviews":    review_count,
    }
