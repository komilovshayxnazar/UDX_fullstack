@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.udx.app.data.NetworkModule
import com.udx.app.data.OrderCreate
import com.udx.app.data.OrderItemCreate
import com.udx.app.ui.viewmodels.CartItem
import com.udx.app.ui.viewmodels.CartViewModel
import com.udx.app.utils.CurrencyFormatter
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CartScreen(
    viewModel: CartViewModel,
    onBack: () -> Unit
) {
    val cartItems by viewModel.cartItems.collectAsState()
    val totalPrice by remember { derivedStateOf { cartItems.sumOf { it.product.price * it.quantity } } }
    val scope = rememberCoroutineScope()

    var showCheckoutDialog by remember { mutableStateOf(false) }
    var deliveryMethod by remember { mutableStateOf("courier") }
    var isPlacingOrder by remember { mutableStateOf(false) }
    var orderError by remember { mutableStateOf<String?>(null) }
    var orderSuccess by remember { mutableStateOf(false) }

    // Sotuvchi bo'yicha guruhlar (backend har buyurtmada bir sotuvchi talab qiladi)
    val sellerGroups by remember { derivedStateOf {
        cartItems.groupBy { it.product.sellerId }
    }}

    if (orderSuccess) {
        AlertDialog(
            onDismissRequest = { orderSuccess = false },
            icon = { Text("✅", style = MaterialTheme.typography.headlineMedium) },
            title = { Text("Buyurtma qabul qilindi!") },
            text = { Text("Buyurtmangiz muvaffaqiyatli joylashtirildi. Sotuvchi siz bilan bog'lanadi.") },
            confirmButton = {
                Button(onClick = { orderSuccess = false; onBack() },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9C27B0))) {
                    Text("Tamom", color = Color.White)
                }
            }
        )
    }

    if (showCheckoutDialog) {
        AlertDialog(
            onDismissRequest = { if (!isPlacingOrder) showCheckoutDialog = false },
            title = { Text("Buyurtmani tasdiqlash") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    cartItems.forEach { item ->
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${item.product.name} x${item.quantity}", style = MaterialTheme.typography.bodyMedium)
                            Text(CurrencyFormatter.formatUzs(item.product.price * item.quantity), style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                    Divider()
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Jami:", fontWeight = FontWeight.Bold)
                        Text(CurrencyFormatter.formatUzs(totalPrice), fontWeight = FontWeight.Bold, color = Color(0xFF9C27B0))
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("Yetkazib berish usuli:", style = MaterialTheme.typography.labelLarge)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = deliveryMethod == "courier", onClick = { deliveryMethod = "courier" })
                        Text("Kuryer")
                        Spacer(modifier = Modifier.width(16.dp))
                        RadioButton(selected = deliveryMethod == "pickup", onClick = { deliveryMethod = "pickup" })
                        Text("O'zi olib ketish")
                    }
                    if (sellerGroups.size > 1) {
                        Text(
                            "⚠️ Savatingizda ${sellerGroups.size} ta sotuvchidan mahsulot bor. ${sellerGroups.size} ta alohida buyurtma yaratiladi.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                    orderError?.let {
                        Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        orderError = null
                        isPlacingOrder = true
                        scope.launch {
                            try {
                                // Har bir sotuvchi uchun alohida buyurtma
                                sellerGroups.values.forEach { items ->
                                    NetworkModule.apiService.createOrder(
                                        OrderCreate(
                                            items = items.map { OrderItemCreate(it.product.id, it.quantity) },
                                            deliveryMethod = deliveryMethod
                                        )
                                    )
                                }
                                viewModel.clearCart()
                                showCheckoutDialog = false
                                orderSuccess = true
                            } catch (e: Exception) {
                                orderError = "Xatolik: ${e.message?.take(80)}"
                            } finally {
                                isPlacingOrder = false
                            }
                        }
                    },
                    enabled = !isPlacingOrder,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9C27B0))
                ) {
                    if (isPlacingOrder) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White, strokeWidth = 2.dp)
                    } else {
                        Text("Tasdiqlash", color = Color.White)
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = { showCheckoutDialog = false }, enabled = !isPlacingOrder) {
                    Text("Bekor")
                }
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("My Cart") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF9C27B0),
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White
                )
            )
        },
        bottomBar = {
            if (cartItems.isNotEmpty()) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shadowElevation = 8.dp
                ) {
                    Column(
                        modifier = Modifier
                            .padding(16.dp)
                            .navigationBarsPadding()
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Total:", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                            Text(CurrencyFormatter.formatUzs(totalPrice), fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFF9C27B0))
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(
                            onClick = { showCheckoutDialog = true },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9C27B0))
                        ) {
                            Text("Checkout", color = Color.White)
                        }
                    }
                }
            }
        }
    ) { padding ->
        if (cartItems.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Default.ShoppingCart,
                        contentDescription = null,
                        modifier = Modifier.size(100.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("Your cart is empty", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 18.sp)
                    Spacer(modifier = Modifier.height(24.dp))
                    Button(onClick = onBack) {
                        Text("Go Shopping")
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                items(cartItems) { item ->
                    CartItemRow(
                        item = item,
                        onUpdateQuantity = { qty -> viewModel.updateQuantity(item.product.id, qty) },
                        onRemove = { viewModel.removeFromCart(item.product.id) }
                    )
                }
            }
        }
    }
}

@Composable
fun CartItemRow(
    item: CartItem,
    onUpdateQuantity: (Int) -> Unit,
    onRemove: () -> Unit
) {
    Card(
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            val product = item.product
            val imageUrl = if (product.image.startsWith("http")) product.image else "https://udx-marketplace.store${product.image}"
            
            AsyncImage(
                model = imageUrl,
                contentDescription = product.name,
                modifier = Modifier.size(80.dp),
                contentScale = ContentScale.Crop
            )
            
            Spacer(modifier = Modifier.width(16.dp))
            
            Column(modifier = Modifier.weight(1f)) {
                Text(product.name, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Text(CurrencyFormatter.formatUzs(product.price), color = Color(0xFF9C27B0), fontWeight = FontWeight.SemiBold)
                
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(top = 8.dp)
                ) {
                    IconButton(
                        onClick = { onUpdateQuantity(item.quantity - 1) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.KeyboardArrowDown, contentDescription = "Decrease")
                    }
                    Text("${item.quantity}", modifier = Modifier.padding(horizontal = 8.dp))
                    IconButton(
                        onClick = { onUpdateQuantity(item.quantity + 1) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.KeyboardArrowUp, contentDescription = "Increase")
                    }
                }
            }
            
            IconButton(onClick = onRemove) {
                Icon(Icons.Default.Delete, contentDescription = "Remove", tint = Color.Red)
            }
        }
    }
}
