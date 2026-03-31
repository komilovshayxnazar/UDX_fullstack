package com.udx.app.data

import com.google.gson.annotations.SerializedName

// Auth Models
data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

data class GoogleAuthUrlResponse(
    @SerializedName("auth_url") val authUrl: String
)

// User Models
data class User(
    val id: String,
    val phone: String,
    val name: String?,
    val role: String,
    val avatar: String?,
    val balance: Double = 0.0
)

data class UserCreate(
    val phone: String,
    val password: String,
    val role: String = "buyer",
    val name: String? = null,
    @SerializedName("telegram_username") val telegramUsername: String? = null
)

data class TelegramOtpRequest(
    @SerializedName("telegram_username") val telegramUsername: String
)

data class TelegramOtpVerify(
    @SerializedName("telegram_username") val telegramUsername: String,
    val code: String
)

data class MessageResponse(
    val detail: String
)

data class PaymentCard(
    val id: String,
    @SerializedName("owner_name") val ownerName: String,
    val last4: String,
    val expiry: String,
    @SerializedName("card_type") val cardType: String
)

// Step 1: tokenize card via mock/real gateway → get card_token
data class CardTokenizeRequest(
    @SerializedName("card_number") val cardNumber: String,
    val expiry: String,
    @SerializedName("owner_name") val ownerName: String
)

data class CardTokenizeResponse(
    @SerializedName("card_token") val cardToken: String,
    val last4: String,
    @SerializedName("card_type") val cardType: String,
    val expiry: String,
    @SerializedName("owner_name") val ownerName: String
)

// Step 2: save tokenized card to our server — full PAN never transmitted
data class PaymentCardCreate(
    @SerializedName("card_token") val cardToken: String,
    val last4: String,
    val expiry: String,
    @SerializedName("owner_name") val ownerName: String,
    @SerializedName("card_type") val cardType: String
)

data class TransactionRecord(
    val id: String,
    val amount: Double,
    val type: String,
    val status: String,
    @SerializedName("transaction_id") val transactionId: String,
    @SerializedName("created_at") val createdAt: String
)

data class AuditLogEntry(
    val id: String,
    val action: String,
    val detail: Map<String, Any>,
    @SerializedName("ip_address") val ipAddress: String,
    val success: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class TransactionRequest(
    val amount: Double,
    @SerializedName("card_id") val cardId: String
)

data class UserUpdate(
    val name: String? = null,
    val avatar: String? = null,
    val description: String? = null
)

data class RoleUpdate(
    val role: String
)

data class PasswordUpdate(
    @SerializedName("current_password") val currentPassword: String,
    @SerializedName("new_password") val newPassword: String
)

data class Category(
    val id: String,
    val name: String,
    val icon: String
)

// Product Models
data class ProductRemote(
    val id: String,
    val name: String,
    val price: Double,
    val unit: String,
    val image: String,
    val description: String,
    @SerializedName("seller_id") val sellerId: String,
    @SerializedName("category_id") val categoryId: String,
    val rating: Float,
    @SerializedName("review_count") val reviewCount: Int,
    val views: Int = 0,
    val sales: Int = 0,
    val gallery: List<String> = emptyList(),
    @SerializedName("is_b2b") val isB2b: Boolean = false
)

data class ProductCreate(
    val name: String,
    val price: Double,
    val unit: String,
    val image: String,
    val description: String,
    @SerializedName("category_id") val categoryId: String,
    @SerializedName("is_b2b") val isB2b: Boolean = false
)

data class InteractionRequest(
    @SerializedName("product_id") val productId: String,
    @SerializedName("interaction_type") val interactionType: String
)

data class UploadResponse(
    val url: String
)

data class PriceHistoryCreate(
    val price: Double
)

data class PriceHistory(
    val id: String,
    @SerializedName("product_id") val productId: String,
    val price: Double,
    val date: String
)

data class ContractRemote(
    val id: String,
    @SerializedName("buyer_id") val buyerId: String,
    @SerializedName("seller_id") val sellerId: String,
    val title: String,
    val description: String?,
    val amount: Double,
    val status: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("buyer_name") val buyerName: String?,
    @SerializedName("seller_name") val sellerName: String?
)
