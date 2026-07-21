@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.StarBorder
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.OrderOut
import com.udx.app.data.OrderStatusUpdate
import com.udx.app.data.ReviewCreate
import com.udx.app.utils.CurrencyFormatter
import kotlinx.coroutines.launch
import retrofit2.HttpException

private fun friendlyOrderError(context: android.content.Context, e: Throwable): String {
    if (e !is HttpException) return context.getString(R.string.err_generic)
    val body = e.response()?.errorBody()?.string() ?: return context.getString(R.string.err_generic)
    return try {
        val json = org.json.JSONObject(body)
        val detail = json.get("detail")
        if (detail is String) {
            val resId = when (detail) {
                "errors.order_not_found" -> R.string.err_order_not_found
                "errors.order_not_yours" -> R.string.err_order_not_yours
                "errors.order_status_invalid_transition" -> R.string.err_order_status_invalid_transition
                "errors.buyer_only_reviews" -> R.string.err_buyer_only_reviews
                "errors.completed_orders_only" -> R.string.err_completed_orders_only
                "errors.seller_mismatch" -> R.string.err_seller_mismatch
                "errors.self_review_forbidden" -> R.string.err_self_review_forbidden
                "errors.review_already_exists" -> R.string.err_review_already_exists
                else -> null
            }
            if (resId != null) context.getString(resId) else detail
        } else {
            json.getJSONArray("detail").getJSONObject(0).getString("msg").removePrefix("Value error, ")
        }
    } catch (_: Exception) {
        context.getString(R.string.err_generic)
    }
}

@Composable
private fun statusColor(status: String): Color = when (status) {
    "new" -> Color(0xFF1565C0)
    "in-process" -> Color(0xFFFF9800)
    "completed" -> Color(0xFF2E7D32)
    "cancelled" -> Color(0xFFE53935)
    else -> Color.Gray
}

@Composable
private fun statusLabel(status: String): String = when (status) {
    "new" -> stringResource(R.string.order_status_new)
    "in-process" -> stringResource(R.string.order_status_in_process)
    "completed" -> stringResource(R.string.order_status_completed)
    "cancelled" -> stringResource(R.string.order_status_cancelled)
    else -> status
}

@Composable
fun OrdersScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var orders by remember { mutableStateOf<List<OrderOut>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var actionError by remember { mutableStateOf<String?>(null) }
    var reviewTarget by remember { mutableStateOf<OrderOut?>(null) }

    suspend fun reload() {
        try {
            orders = NetworkModule.apiService.getOrders()
        } catch (_: Exception) {
        }
    }

    LaunchedEffect(Unit) {
        isLoading = true
        reload()
        isLoading = false
    }

    fun changeStatus(order: OrderOut, newStatus: String) {
        scope.launch {
            try {
                NetworkModule.apiService.updateOrderStatus(order.id, OrderStatusUpdate(newStatus))
                reload()
            } catch (e: Exception) {
                actionError = friendlyOrderError(context, e)
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.orders_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF9C27B0),
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White
                )
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = Color(0xFF9C27B0))
                }
                orders.isEmpty() -> Column(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.ShoppingCart,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.5f)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(stringResource(R.string.orders_empty_title), style = MaterialTheme.typography.headlineSmall)
                    Text(
                        stringResource(R.string.orders_empty_desc),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                }
                else -> LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(orders, key = { it.id }) { order ->
                        OrderCard(
                            order = order,
                            onAccept = { changeStatus(order, "in-process") },
                            onComplete = { changeStatus(order, "completed") },
                            onCancel = { changeStatus(order, "cancelled") },
                            onReview = { reviewTarget = order }
                        )
                    }
                }
            }
        }
    }

    if (actionError != null) {
        AlertDialog(
            onDismissRequest = { actionError = null },
            confirmButton = {
                TextButton(onClick = { actionError = null }) { Text(stringResource(R.string.confirm)) }
            },
            text = { Text(actionError!!) }
        )
    }

    reviewTarget?.let { order ->
        ReviewDialog(
            order = order,
            onDismiss = { reviewTarget = null },
            onSubmitted = {
                reviewTarget = null
                scope.launch { reload() }
            },
            onError = { msg -> actionError = msg }
        )
    }
}

@Composable
private fun OrderCard(
    order: OrderOut,
    onAccept: () -> Unit,
    onComplete: () -> Unit,
    onCancel: () -> Unit,
    onReview: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (order.isBuyer) (order.sellerName ?: stringResource(R.string.seller))
                           else (order.buyerName ?: stringResource(R.string.buyer)),
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = statusColor(order.status).copy(alpha = 0.12f)
                ) {
                    Text(
                        statusLabel(order.status),
                        color = statusColor(order.status),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(order.date.take(10), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.height(8.dp))
            order.items.forEach { item ->
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("${item.productName ?: item.productId} x${item.quantity}", fontSize = 14.sp)
                    Text(CurrencyFormatter.formatUzs(item.priceAtPurchase * item.quantity), fontSize = 14.sp)
                }
            }
            Divider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outlineVariant)
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.order_total_label), fontWeight = FontWeight.Bold)
                Text(CurrencyFormatter.formatUzs(order.total), fontWeight = FontWeight.Bold, color = Color(0xFF9C27B0))
            }

            val canAccept = !order.isBuyer && order.status == "new"
            val canComplete = !order.isBuyer && order.status == "in-process"
            val canCancel = order.status == "new" || order.status == "in-process"
            val canReview = order.isBuyer && order.status == "completed" && !order.hasReview

            if (canAccept || canComplete || canCancel || canReview) {
                Spacer(modifier = Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (canAccept) {
                        Button(onClick = onAccept, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9C27B0))) {
                            Text(stringResource(R.string.order_accept))
                        }
                    }
                    if (canComplete) {
                        Button(onClick = onComplete, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))) {
                            Text(stringResource(R.string.order_mark_completed))
                        }
                    }
                    if (canReview) {
                        Button(onClick = onReview, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9C27B0))) {
                            Text(stringResource(R.string.order_leave_review))
                        }
                    }
                    if (canCancel) {
                        OutlinedButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewDialog(
    order: OrderOut,
    onDismiss: () -> Unit,
    onSubmitted: () -> Unit,
    onError: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var rating by remember { mutableStateOf(5) }
    var comment by remember { mutableStateOf("") }
    var isSubmitting by remember { mutableStateOf(false) }
    var localError by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = { if (!isSubmitting) onDismiss() },
        title = { Text(stringResource(R.string.review_dialog_title)) },
        text = {
            Column {
                Text(stringResource(R.string.review_rating_label), style = MaterialTheme.typography.labelMedium)
                Row {
                    repeat(5) { i ->
                        IconButton(onClick = { rating = i + 1 }) {
                            Icon(
                                imageVector = if (i < rating) Icons.Default.Star else Icons.Default.StarBorder,
                                contentDescription = null,
                                tint = Color(0xFFFFC107)
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                OutlinedTextField(
                    value = comment,
                    onValueChange = { comment = it },
                    label = { Text(stringResource(R.string.review_comment_hint)) },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3
                )
                if (localError != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(localError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    localError = null
                    if (comment.trim().length < 10) {
                        localError = context.getString(R.string.review_comment_too_short)
                        return@Button
                    }
                    isSubmitting = true
                    scope.launch {
                        try {
                            NetworkModule.apiService.createReview(
                                ReviewCreate(
                                    sellerId = order.sellerId ?: "",
                                    orderId = order.id,
                                    productId = order.items.firstOrNull()?.productId,
                                    rating = rating,
                                    comment = comment.trim()
                                )
                            )
                            onSubmitted()
                        } catch (e: Exception) {
                            isSubmitting = false
                            onError(friendlyOrderError(context, e))
                        }
                    }
                },
                enabled = !isSubmitting
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Color.White, strokeWidth = 2.dp)
                } else {
                    Text(stringResource(R.string.review_submit))
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !isSubmitting) {
                Text(stringResource(R.string.cancel))
            }
        }
    )
}
