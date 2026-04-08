package com.udx.app.data

import retrofit2.http.DELETE
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.Part
import okhttp3.MultipartBody

interface ApiService {
    @FormUrlEncoded
    @POST("token")
    suspend fun login(
        @Field("username") phone: String,
        @Field("password") password: String
    ): TokenResponse

    @GET("products/")
    suspend fun getProducts(
        @retrofit2.http.Query("is_b2b") isB2b: Boolean? = null,
        @retrofit2.http.Query("category_id") categoryId: String? = null,
        @retrofit2.http.Query("q") query: String? = null
    ): List<ProductRemote>

    @GET("categories/")
    suspend fun getCategories(): List<Category>

    @POST("auth/otp/request")
    suspend fun requestTelegramOtp(@Body body: TelegramOtpRequest): MessageResponse

    @POST("auth/otp/verify")
    suspend fun verifyTelegramOtp(@Body body: TelegramOtpVerify): MessageResponse

    @POST("users/")
    suspend fun register(@Body user: UserCreate): User

    @GET("auth/google/login")
    suspend fun getGoogleLoginUrl(): com.udx.app.data.GoogleAuthUrlResponse

    @GET("auth/google/register")
    suspend fun getGoogleRegisterUrl(): com.udx.app.data.GoogleAuthUrlResponse

    @GET("auth/google/callback")
    suspend fun handleGoogleCallback(
        @retrofit2.http.Query("code") code: String,
        @retrofit2.http.Query("state") state: String?
    ): GoogleCallbackResponse

    @GET("users/me")
    suspend fun getMe(): User

    @PUT("users/me")
    suspend fun updateMe(@Body update: UserUpdate): User

    @PUT("users/me/password")
    suspend fun updatePassword(@Body update: PasswordUpdate): MessageResponse

    @PUT("users/me/role")
    suspend fun updateRole(@Body update: RoleUpdate): User

    // Mock gateway tokenization — in production replaced by real gateway SDK
    @POST("payments/tokenize")
    suspend fun tokenizeCard(@Body card: CardTokenizeRequest): CardTokenizeResponse

    @GET("payments/transactions")
    suspend fun getTransactions(): List<TransactionRecord>

    @GET("users/me/cards")
    suspend fun getCards(): List<PaymentCard>

    @POST("users/me/cards")
    suspend fun addCard(@Body card: PaymentCardCreate): PaymentCard

    @DELETE("users/me/cards/{cardId}")
    suspend fun deleteCard(@retrofit2.http.Path("cardId") cardId: String): MessageResponse

    // Deposit with idempotency key to prevent double charges
    @POST("users/me/balance/deposit")
    suspend fun depositBalance(
        @Body request: TransactionRequest,
        @retrofit2.http.Header("X-Idempotency-Key") idempotencyKey: String
    ): User

    @POST("users/me/balance/withdraw")
    suspend fun withdrawBalance(@Body request: TransactionRequest): User

    @GET("payments/audit")
    suspend fun getAuditLog(): List<AuditLogEntry>

    @POST("products/")
    suspend fun createProduct(@Body product: ProductCreate): ProductRemote

    @Multipart
    @POST("upload/image/")
    suspend fun uploadImage(@Part file: MultipartBody.Part): UploadResponse

    @GET("products/{id}/prices/")
    suspend fun getPriceHistory(@retrofit2.http.Path("id") productId: String): List<PriceHistory>

    @POST("products/{id}/prices/")
    suspend fun addPriceHistory(
        @retrofit2.http.Path("id") productId: String,
        @Body priceData: PriceHistoryCreate
    ): PriceHistory

    @GET("contracts/")
    suspend fun getContracts(): List<ContractRemote>

    @POST("products/interactions/")
    suspend fun recordInteraction(@Body interaction: InteractionRequest): retrofit2.Response<Unit>

    @GET("products/recommendations/")
    suspend fun getRecommendations(@retrofit2.http.Query("limit") limit: Int = 10): List<ProductRemote>

    @POST("orders/")
    suspend fun createOrder(@Body order: OrderCreate): OrderOut

    @GET("orders/")
    suspend fun getOrders(): List<OrderOut>

    @GET("users/{userId}/public")
    suspend fun getPublicProfile(@retrofit2.http.Path("userId") userId: String): PublicUserProfile

    @POST("reviews/")
    suspend fun createReview(@Body review: ReviewCreate): ReviewRemote

    @GET("reviews/seller/{sellerId}")
    suspend fun getSellerReviews(
        @retrofit2.http.Path("sellerId") sellerId: String,
        @retrofit2.http.Query("skip") skip: Int = 0,
        @retrofit2.http.Query("limit") limit: Int = 20
    ): List<ReviewRemote>

    @POST("fraud-reports/")
    suspend fun reportFraud(@Body report: FraudReportCreate): MessageResponse

    @GET("chats/")
    suspend fun getChats(): List<ChatRemote>

    @GET("chats/{chatId}/messages")
    suspend fun getChatMessages(@retrofit2.http.Path("chatId") chatId: String): List<MessageRemote>

    @POST("chats/{chatId}/messages")
    suspend fun sendMessage(
        @retrofit2.http.Path("chatId") chatId: String,
        @retrofit2.http.Query("message_text") text: String
    ): MessageRemote
}
