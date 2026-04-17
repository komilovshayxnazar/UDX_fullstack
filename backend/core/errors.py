"""
Markaziy xato kodlari.

Backend hech qachon foydalanuvchiga to'g'ridan matn qaytarmaydi —
faqat kod. Frontend kodni o'z tiliga tarjima qiladi: t(error.detail)

Foydalanish:
    from core.errors import E
    raise HTTPException(status_code=400, detail=E.OTP_EXPIRED)
"""


class E:
    # ── Auth ────────────────────────────────────────────────────────────────
    OTP_NOT_FOUND           = "errors.otp_not_found"
    OTP_EXPIRED             = "errors.otp_expired"
    OTP_TOO_MANY_ATTEMPTS   = "errors.otp_too_many_attempts"
    OTP_INVALID             = "errors.otp_invalid"
    INCORRECT_CREDENTIALS   = "errors.incorrect_credentials"
    GOOGLE_TOKEN_FAILED     = "errors.google_token_failed"
    GOOGLE_USERINFO_FAILED  = "errors.google_userinfo_failed"
    TELEGRAM_USER_NOT_FOUND = "errors.telegram_user_not_found"
    TELEGRAM_OTP_FAILED     = "errors.telegram_otp_failed"

    # ── Users ───────────────────────────────────────────────────────────────
    TELEGRAM_OTP_NOT_VERIFIED = "errors.telegram_otp_not_verified"
    PHONE_OTP_NOT_VERIFIED    = "errors.phone_otp_not_verified"
    PHONE_ALREADY_REGISTERED  = "errors.phone_already_registered"
    USER_NOT_FOUND            = "errors.user_not_found"
    OAUTH_NO_PASSWORD         = "errors.oauth_no_password"
    INCORRECT_PASSWORD        = "errors.incorrect_password"
    ROLE_FORBIDDEN            = "errors.role_forbidden"

    # ── Payments / Wallet ───────────────────────────────────────────────────
    AMOUNT_MUST_BE_POSITIVE = "errors.amount_must_be_positive"
    CARD_NOT_FOUND          = "errors.card_not_found"
    PAYMENT_DECLINED        = "errors.payment_declined"
    INSUFFICIENT_FUNDS      = "errors.insufficient_funds"

    # ── Products ────────────────────────────────────────────────────────────
    INVALID_IMAGE_TYPE = "errors.invalid_image_type"
    FILE_TOO_LARGE     = "errors.file_too_large"
    PRODUCT_NOT_FOUND  = "errors.product_not_found"
    SELLER_ONLY        = "errors.seller_only"

    # ── Orders ──────────────────────────────────────────────────────────────
    SINGLE_SELLER_CONSTRAINT = "errors.single_seller_constraint"
    ORDER_NOT_FOUND          = "errors.order_not_found"
    ORDER_NOT_YOURS          = "errors.order_not_yours"

    # ── Reviews ─────────────────────────────────────────────────────────────
    BUYER_ONLY_REVIEWS    = "errors.buyer_only_reviews"
    COMPLETED_ORDERS_ONLY = "errors.completed_orders_only"
    SELLER_MISMATCH       = "errors.seller_mismatch"
    SELF_REVIEW_FORBIDDEN = "errors.self_review_forbidden"
    REVIEW_ALREADY_EXISTS = "errors.review_already_exists"

    # ── Fraud ────────────────────────────────────────────────────────────────
    SPECIFY_REPORT_TARGET = "errors.specify_report_target"
    USER_REPORT_LIMIT     = "errors.user_report_limit"
    PRODUCT_REPORT_LIMIT  = "errors.product_report_limit"

    # ── Contracts ────────────────────────────────────────────────────────────
    BUYER_NOT_FOUND    = "errors.buyer_not_found"
    CONTRACT_NOT_FOUND = "errors.contract_not_found"
    ACCESS_DENIED      = "errors.access_denied"

    # ── Chat ─────────────────────────────────────────────────────────────────
    CHAT_NOT_FOUND             = "errors.chat_not_found"
    CHAT_PERMISSION_DENIED     = "errors.chat_not_found"

    # ── Weather ──────────────────────────────────────────────────────────────
    WEATHER_API_NOT_CONFIGURED = "errors.weather_api_not_configured"
    WEATHER_FETCH_FAILED       = "errors.weather_fetch_failed"
