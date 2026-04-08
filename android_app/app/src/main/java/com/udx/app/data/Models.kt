package com.udx.app.data

import com.google.gson.annotations.SerializedName

// Chat Models
data class ChatRemote(
    val id: String,
    @SerializedName("other_user") val otherUser: ChatUser,
    @SerializedName("last_message") val lastMessage: String?,
    @SerializedName("last_message_time") val lastMessageTime: String?,
    @SerializedName("unread_count") val unreadCount: Int = 0,
    @SerializedName("product_id") val productId: String?
)

data class ChatUser(
    val id: String,
    val name: String?,
    val avatar: String?,
    val role: String?
)

data class MessageRemote(
    val id: String,
    @SerializedName("chat_id") val chatId: String,
    @SerializedName("sender_id") val senderId: String,
    val text: String,
    val timestamp: String?
)

// Auth Models
data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

data class GoogleAuthUrlResponse(
    @SerializedName("auth_url") val authUrl: String
)

data class GoogleCallbackResponse(
    val token: String? = null,
    val registered: Boolean = false,
    val error: String? = null
)

// User Models
data class User(
    val id: String,
    val phone: String,
    val name: String?,
    val role: String,
    val avatar: String?,
    val balance: Double = 0.0,
    @SerializedName("is_public") val isPublic: Boolean = true
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
    val description: String? = null,
    @SerializedName("is_public") val isPublic: Boolean? = null
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

data class SellerPublic(
    val id: String,
    val name: String?,
    val avatar: String?,
    val rating: Float = 0f,
    @SerializedName("review_count") val reviewCount: Int = 0,
    @SerializedName("is_online") val isOnline: Boolean = false,
    @SerializedName("is_verified") val isVerified: Boolean = false
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
    @SerializedName("is_b2b") val isB2b: Boolean = false,
    val seller: SellerPublic? = null
)

data class ReviewRemote(
    val id: String,
    @SerializedName("reviewer_id") val reviewerId: String,
    @SerializedName("reviewer_name") val reviewerName: String?,
    @SerializedName("seller_id") val sellerId: String,
    @SerializedName("order_id") val orderId: String,
    @SerializedName("product_id") val productId: String?,
    val rating: Int,
    val comment: String,
    @SerializedName("is_verified_purchase") val isVerifiedPurchase: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class ReviewCreate(
    @SerializedName("seller_id") val sellerId: String,
    @SerializedName("order_id") val orderId: String,
    @SerializedName("product_id") val productId: String? = null,
    val rating: Int,
    val comment: String
)

data class FraudReportCreate(
    @SerializedName("target_user_id") val targetUserId: String? = null,
    @SerializedName("target_product_id") val targetProductId: String? = null,
    val reason: String
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

data class PublicUserProfile(
    val id: String,
    val name: String?,
    val avatar: String?,
    val description: String?,
    val rating: Float,
    @SerializedName("review_count") val reviewCount: Int,
    @SerializedName("is_online") val isOnline: Boolean,
    @SerializedName("is_verified") val isVerified: Boolean,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("total_orders") val totalOrders: Int,
    @SerializedName("successful_orders") val successfulOrders: Int,
    @SerializedName("unsuccessful_orders") val unsuccessfulOrders: Int,
    @SerializedName("in_progress_orders") val inProgressOrders: Int,
    val reviews: List<ReviewRemote> = emptyList()
)

data class OrderItemCreate(
    @SerializedName("product_id") val productId: String,
    val quantity: Int
)

data class OrderCreate(
    val items: List<OrderItemCreate>,
    @SerializedName("delivery_method") val deliveryMethod: String = "courier"
)

data class OrderOut(
    val id: String,
    val date: String,
    val status: String,
    val total: Double,
    val items: List<OrderItemCreate>
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
