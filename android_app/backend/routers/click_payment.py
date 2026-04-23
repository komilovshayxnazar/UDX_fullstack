"""
click_payment.py — Click Merchant API integratsiyasi.

To'lov oqimi:
  1. POST /payments/click/create  — foydalanuvchi balansni to'ldirmoqchi
     → merchant_trans_id (UUID) yaratiladi, Click to'lov sahifasiga redirect URL qaytariladi
  2. Click → POST /payments/click/prepare  — to'lov boshlanishidan oldin Click so'raydi
  3. Click → POST /payments/click/complete — to'lov tugagach Click tasdiqlaydi → balans oshadi

Imzo (MD5):
  prepare:  MD5(click_trans_id + service_id + secret + merchant_trans_id + amount + action + sign_time)
  complete: MD5(click_trans_id + service_id + secret + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)

Click xato kodlari:
  0   — muvaffaqiyatli
  -1  — SIGN_FAILED
  -2  — ORDER_NOT_FOUND
  -3  — ALREADY_PAID
  -4  — UNABLE_PERFORM_OPERATION
  -5  — USER_DOES_NOT_EXIST
  -6  — TRANSACTION_CANCELLED
  -9  — WRONG_AMOUNT
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

import models
import schemas
from core.dependencies import get_current_user
from services import wallet_service

router = APIRouter(prefix="/payments/click", tags=["click"])

# ── Sozlamalar ────────────────────────────────────────────────────────────────

CLICK_SERVICE_ID      = os.getenv("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID     = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY      = os.getenv("CLICK_SECRET_KEY", "")
CLICK_MERCHANT_USER_ID = os.getenv("CLICK_MERCHANT_USER_ID", "")
CLICK_RETURN_URL      = os.getenv("CLICK_RETURN_URL", "https://udx-marketplace.store/wallet")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _verify_prepare_sign(
    click_trans_id: str,
    merchant_trans_id: str,
    amount: str,
    action: str,
    sign_time: str,
    sign_string: str,
) -> bool:
    expected = _md5(
        f"{click_trans_id}{CLICK_SERVICE_ID}{CLICK_SECRET_KEY}"
        f"{merchant_trans_id}{amount}{action}{sign_time}"
    )
    return expected == sign_string


def _verify_complete_sign(
    click_trans_id: str,
    merchant_trans_id: str,
    merchant_prepare_id: str,
    amount: str,
    action: str,
    sign_time: str,
    sign_string: str,
) -> bool:
    expected = _md5(
        f"{click_trans_id}{CLICK_SERVICE_ID}{CLICK_SECRET_KEY}"
        f"{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
    )
    return expected == sign_string


def _err(code: int, note: str, **extra) -> JSONResponse:
    return JSONResponse({"error": code, "error_note": note, **extra})


# ── 1. To'lov URL yaratish ────────────────────────────────────────────────────

@router.post("/create", response_model=schemas.ClickPaymentCreate)
async def create_click_payment(
    body: schemas.ClickPaymentRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Foydalanuvchi balansi to'ldirish uchun Click to'lov URL'ini yaratadi.
    Karta shart emas — foydalanuvchi Click ilovasi, my.click.uz yoki USSD orqali to'laydi.
    """
    if body.amount <= 0:
        return JSONResponse(status_code=400, content={"detail": "Amount must be positive"})

    merchant_trans_id = uuid.uuid4().hex

    txn = models.ClickTransaction(
        user_id=str(current_user.id),
        amount=body.amount,
        merchant_trans_id=merchant_trans_id,
    )
    await txn.insert()

    pay_url = (
        f"https://my.click.uz/services/pay"
        f"?service_id={CLICK_SERVICE_ID}"
        f"&merchant_id={CLICK_MERCHANT_ID}"
        f"&amount={body.amount}"
        f"&transaction_param={merchant_trans_id}"
        f"&return_url={CLICK_RETURN_URL}"
    )

    return schemas.ClickPaymentCreate(
        merchant_trans_id=merchant_trans_id,
        pay_url=pay_url,
    )


# ── 2. Prepare webhook (Click tomondan keladi) ────────────────────────────────

@router.post("/prepare")
async def click_prepare(
    click_trans_id: str = Form(...),
    service_id: str = Form(...),
    click_paydoc_id: str = Form(...),
    merchant_trans_id: str = Form(...),
    amount: str = Form(...),
    action: str = Form(...),
    error: str = Form(...),
    error_note: str = Form(...),
    sign_time: str = Form(...),
    sign_string: str = Form(...),
):
    # 1. Imzo tekshiruvi
    if not _verify_prepare_sign(
        click_trans_id, merchant_trans_id, amount, action, sign_time, sign_string
    ):
        return _err(-1, "SIGN_FAILED",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 2. Action = 0 bo'lishi shart
    if action != "0":
        return _err(-4, "UNABLE_PERFORM_OPERATION",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 3. Tranzaksiyani topish
    txn = await models.ClickTransaction.find_one(
        models.ClickTransaction.merchant_trans_id == merchant_trans_id
    )
    if not txn:
        return _err(-2, "ORDER_NOT_FOUND",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 4. Allaqachon to'langan
    if txn.status == models.ClickTxnStatus.completed:
        return _err(-3, "ALREADY_PAID",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 5. Bekor qilingan
    if txn.status == models.ClickTxnStatus.cancelled:
        return _err(-6, "TRANSACTION_CANCELLED",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 6. Summa mosligini tekshirish (±0.01 tolerans)
    if abs(float(amount) - txn.amount) > 0.01:
        return _err(-9, "WRONG_AMOUNT",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 7. Prepare holatiga o'tkazish
    txn.status = models.ClickTxnStatus.prepared
    txn.click_trans_id = click_trans_id
    txn.click_paydoc_id = click_paydoc_id
    txn.updated_at = datetime.now(timezone.utc)
    await txn.save()

    return JSONResponse({
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "merchant_prepare_id": str(txn.id),
        "error": 0,
        "error_note": "Success",
    })


# ── 3. Complete webhook (Click tomondan keladi) ───────────────────────────────

@router.post("/complete")
async def click_complete(
    click_trans_id: str = Form(...),
    service_id: str = Form(...),
    click_paydoc_id: str = Form(...),
    merchant_trans_id: str = Form(...),
    merchant_prepare_id: str = Form(...),
    amount: str = Form(...),
    action: str = Form(...),
    error: str = Form(...),
    error_note: str = Form(...),
    sign_time: str = Form(...),
    sign_string: str = Form(...),
):
    # 1. Imzo tekshiruvi
    if not _verify_complete_sign(
        click_trans_id, merchant_trans_id, merchant_prepare_id,
        amount, action, sign_time, sign_string
    ):
        return _err(-1, "SIGN_FAILED",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 2. Action = 1 bo'lishi shart
    if action != "1":
        return _err(-4, "UNABLE_PERFORM_OPERATION",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 3. Tranzaksiyani topish
    txn = await models.ClickTransaction.find_one(
        models.ClickTransaction.merchant_trans_id == merchant_trans_id
    )
    if not txn:
        return _err(-2, "ORDER_NOT_FOUND",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 4. Click tomonidan xato bo'lsa — bekor qilish
    if int(error) < 0:
        txn.status = models.ClickTxnStatus.cancelled
        txn.updated_at = datetime.now(timezone.utc)
        await txn.save()
        return _err(-6, "TRANSACTION_CANCELLED",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 5. Allaqachon to'langan
    if txn.status == models.ClickTxnStatus.completed:
        return _err(-3, "ALREADY_PAID",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 6. Prepare bosqichi o'tmagan bo'lsa
    if txn.status != models.ClickTxnStatus.prepared:
        return _err(-4, "UNABLE_PERFORM_OPERATION",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 7. Summa tekshiruvi
    if abs(float(amount) - txn.amount) > 0.01:
        return _err(-9, "WRONG_AMOUNT",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 8. Foydalanuvchini topish
    user = await models.User.get(txn.user_id)
    if not user:
        return _err(-5, "USER_DOES_NOT_EXIST",
                    click_trans_id=click_trans_id, merchant_trans_id=merchant_trans_id)

    # 9. Balansni oshirish
    await wallet_service.credit(
        user=user,
        amount=txn.amount,
        card_token=f"click_{click_trans_id}",
        idempotency_key=merchant_trans_id,
    )

    # 10. Tranzaksiyani yakunlash
    txn.status = models.ClickTxnStatus.completed
    txn.updated_at = datetime.now(timezone.utc)
    await txn.save()

    return JSONResponse({
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "merchant_confirm_id": str(txn.id),
        "error": 0,
        "error_note": "Success",
    })
