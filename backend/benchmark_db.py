"""
Database benchmark: shifrlangan vs shifrsiz ma'lumot yozish/o'qish/o'chirish tezligi.

Testlar:
  - Plain   : oddiy matn (shifrsiz)
  - Fernet  : simmetrik AES-128-CBC shifrlash (cryptography.fernet)
  - AES-GCM : AES-256-GCM (autentifikatsiyali shifrlash)

Har bir rejimda 3 ta operatsiya:
  INSERT  N ta hujjat
  FIND    N ta hujjat ID orqali
  DELETE  N ta hujjat
"""

import asyncio
import os
import time
import statistics
import base64
import json

from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ─── Sozlamalar ──────────────────────────────────────────────────────────────
MONGO_URL   = "mongodb://localhost:27017/udx_bench"
COLLECTION  = "bench_users"
ROUNDS      = 5          # har bir test necha marta takrorlanadi
N           = 500        # har bir roundda nechta hujjat

# ─── Shifrlash kalitlari ─────────────────────────────────────────────────────
FERNET_KEY  = Fernet.generate_key()
fernet      = Fernet(FERNET_KEY)

AESGCM_KEY  = AESGCM.generate_key(bit_length=256)
aesgcm      = AESGCM(AESGCM_KEY)

# ─── Namuna ma'lumot ─────────────────────────────────────────────────────────
SAMPLE_USER = {
    "name":    "Alisher Karimov",
    "phone":   "+998901234567",
    "email":   "alisher@example.com",
    "address": "Toshkent, Chilonzor tumani, 12-uy",
    "tin":     "123456789",
    "balance": 250000.0,
}
PLAIN_JSON = json.dumps(SAMPLE_USER, ensure_ascii=False)

def encrypt_fernet(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt_fernet(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

def encrypt_aesgcm(text: str) -> str:
    nonce = os.urandom(12)
    ct    = aesgcm.encrypt(nonce, text.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_aesgcm(blob: str) -> str:
    raw   = base64.b64decode(blob.encode())
    nonce = raw[:12]
    ct    = raw[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()

# ─── Yordamchi ───────────────────────────────────────────────────────────────
def make_doc_plain(i: int) -> dict:
    d = SAMPLE_USER.copy()
    d["_bench_i"] = i
    return d

def make_doc_fernet(i: int) -> dict:
    return {"_bench_i": i, "payload": encrypt_fernet(PLAIN_JSON)}

def make_doc_aesgcm(i: int) -> dict:
    return {"_bench_i": i, "payload": encrypt_aesgcm(PLAIN_JSON)}

# ─── Bench funksiyasi ─────────────────────────────────────────────────────────
async def run_bench(col, make_doc_fn, decrypt_fn=None, label="") -> dict:
    insert_times = []
    find_times   = []
    delete_times = []

    for _ in range(ROUNDS):
        docs   = [make_doc_fn(i) for i in range(N)]
        ids    = []

        # INSERT
        t0 = time.perf_counter()
        result = await col.insert_many(docs)
        insert_times.append(time.perf_counter() - t0)
        ids = result.inserted_ids

        # FIND + decrypt (agar kerak bo'lsa)
        t0 = time.perf_counter()
        cursor = col.find({"_id": {"$in": ids}})
        fetched = await cursor.to_list(length=N)
        if decrypt_fn:
            for doc in fetched:
                decrypt_fn(doc["payload"])
        find_times.append(time.perf_counter() - t0)

        # DELETE
        t0 = time.perf_counter()
        await col.delete_many({"_id": {"$in": ids}})
        delete_times.append(time.perf_counter() - t0)

    def stats(lst):
        ms = [x * 1000 for x in lst]   # sekunddan millisekund
        return {
            "min_ms":  round(min(ms), 2),
            "max_ms":  round(max(ms), 2),
            "avg_ms":  round(statistics.mean(ms), 2),
            "std_ms":  round(statistics.stdev(ms), 2) if len(ms) > 1 else 0,
        }

    return {
        "label":  label,
        "N":      N,
        "rounds": ROUNDS,
        "insert": stats(insert_times),
        "find":   stats(find_times),
        "delete": stats(delete_times),
    }

# ─── Natijani chop etish ─────────────────────────────────────────────────────
def print_table(results: list[dict]):
    ops = ["insert", "find", "delete"]
    metrics = ["min_ms", "avg_ms", "max_ms", "std_ms"]
    col_w = 12

    header_label = f"{'Operatsiya':<10} {'Metrika':<10}"
    for r in results:
        header_label += f"  {r['label']:>{col_w}}"
    print("\n" + "=" * len(header_label))
    print(f"  N = {N} ta hujjat  |  {ROUNDS} ta round o'rtachasi")
    print("=" * len(header_label))
    print(header_label)
    print("-" * len(header_label))

    for op in ops:
        for m in metrics:
            row = f"{op:<10} {m:<10}"
            vals = []
            for r in results:
                v = r[op][m]
                row += f"  {v:>{col_w}.2f}"
                vals.append(v)
            # eng tez ustunni yashil, eng sekin ustunni qizil belgilash (avg_ms uchun)
            if m == "avg_ms":
                min_v = min(vals)
                max_v = max(vals)
                row += f"   ← {'✓ eng tez' if vals[0] == min_v else '✗ eng sekin' if vals[0] == max_v else ''}"
            print(row)
        print()

    # Nisbiy tezlik (Plain = 1.0 bazis)
    print("─" * len(header_label))
    print(f"  Nisbiy tezlik (Plain = 1.0x)  —  kichik = tezroq")
    print("─" * len(header_label))
    base = results[0]
    for op in ops:
        row = f"{op:<10} {'overhead':<10}"
        for r in results:
            ratio = r[op]["avg_ms"] / base[op]["avg_ms"]
            row += f"  {ratio:>{col_w}.3f}x"
        print(row)
    print("=" * len(header_label))

# ─── Asosiy ──────────────────────────────────────────────────────────────────
async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db     = client["udx_bench"]
    col    = db[COLLECTION]
    await col.drop()   # toza boshlanish

    print("\n🔄  Benchmark boshlandi...")
    print(f"    MongoDB : {MONGO_URL}")
    print(f"    Hujjat  : {N} ta  |  Round : {ROUNDS}")

    r_plain  = await run_bench(col, make_doc_plain,  None,            label="Plain")
    r_fernet = await run_bench(col, make_doc_fernet, decrypt_fernet,  label="Fernet(AES-128)")
    r_aesgcm = await run_bench(col, make_doc_aesgcm, decrypt_aesgcm,  label="AES-256-GCM")

    await col.drop()   # tozalash
    client.close()

    print_table([r_plain, r_fernet, r_aesgcm])

    # JSON natija ham saqlash
    out = {"plain": r_plain, "fernet": r_fernet, "aesgcm": r_aesgcm}
    with open("benchmark_results.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\n📄  To'liq natija: benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(main())
