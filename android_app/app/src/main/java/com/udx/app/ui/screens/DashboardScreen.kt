@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import android.app.Activity
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.ProductRemote
import com.udx.app.data.InteractionRequest
import com.udx.app.utils.LocaleHelper
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onLogout: () -> Unit = {},
    onAddProduct: () -> Unit = {},
    onNavigateToMessages: () -> Unit = {},
    onNavigateToCart: () -> Unit = {},
    onNavigateToSettings: () -> Unit = {},
    onNavigateToCategory: (String, String) -> Unit = { _, _ -> },
    onAddToCart: (com.udx.app.data.ProductRemote) -> Unit = {},
    onNavigateToSeller: (String) -> Unit = {},
    cartItemCount: Int = 0,
    isSeller: Boolean = false,
    onSwitchRole: () -> Unit = {}
) {
    val context = LocalContext.current
    var searchQuery by remember { mutableStateOf("") }
    var categories by remember { mutableStateOf<List<com.udx.app.data.Category>>(emptyList()) }
    var selectedCategoryId by remember { mutableStateOf<String?>(null) }
    var isLoadingCategories by remember { mutableStateOf(true) }
    var unreadMessageCount by remember { mutableStateOf(0) }
    var products by remember { mutableStateOf<List<ProductRemote>>(emptyList()) }
    var isLoadingProducts by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    var showLanguageDialog by remember { mutableStateOf(false) }
    var currentLanguage by remember { mutableStateOf(LocaleHelper.getLanguage(context)) }

    val languages = listOf(
        "uz" to "O'zbek",
        "ru" to "Русский",
        "en" to "English",
        "kk" to "Қазақша",
        "ky" to "Кыргызча",
        "tg" to "Тоҷикӣ",
        "de" to "Deutsch",
        "es" to "Español",
        "fr" to "Français"
    )

    LaunchedEffect(Unit) {
        try {
            categories = NetworkModule.apiService.getCategories()
        } catch (e: Exception) {
            // Fallback if needed or just empty
        } finally {
            isLoadingCategories = false
        }
        try {
            val chats = NetworkModule.apiService.getChats()
            unreadMessageCount = chats.sumOf { it.unreadCount }
        } catch (_: Exception) {}
    }

    LaunchedEffect(selectedCategoryId, searchQuery) {
        isLoadingProducts = true
        kotlinx.coroutines.delay(300) // debounce
        try {
            products = NetworkModule.apiService.getProducts(
                categoryId = selectedCategoryId,
                query = searchQuery.trim().ifEmpty { null }
            )
        } catch (_: Exception) {
            products = emptyList()
        } finally {
            isLoadingProducts = false
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // ... (purple top bar code remains same)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF9C27B0))
                .padding(bottom = 16.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
            ) {
                // Top Row: Title & Actions
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 16.dp, bottom = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // App Title
                    Column {
                        Text(
                            text = "UDX",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Agricultural\nMarketplace",
                            color = Color.White,
                            fontSize = 14.sp
                        )
                    }

                    // Actions
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Surface(
                            shape = RoundedCornerShape(16.dp),
                            color = Color.White.copy(alpha = 0.2f),
                            modifier = Modifier
                                .padding(end = 4.dp)
                                .clickable { onSwitchRole() }
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    if (isSeller) Icons.Default.ShoppingCart else Icons.Default.Store,
                                    contentDescription = if (isSeller) "Switch to Buyer" else "Switch to Seller",
                                    tint = Color.White,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    if (isSeller) "Buyer" else "Seller",
                                    color = Color.White,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }

                        // Icons
                        BadgedBox(
                            badge = {
                                if (unreadMessageCount > 0) {
                                    Badge(containerColor = Color.Red) {
                                        Text(
                                            if (unreadMessageCount > 99) "99+" else unreadMessageCount.toString(),
                                            color = Color.White
                                        )
                                    }
                                }
                            },
                            modifier = Modifier.clickable { onNavigateToMessages() }
                        ) {
                            Icon(Icons.Outlined.Email, "Messages", tint = Color.White)
                        }
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color.White.copy(alpha = 0.2f),
                            modifier = Modifier.clickable { showLanguageDialog = true }
                        ) {
                            Text(
                                text = currentLanguage.uppercase(),
                                color = Color.White,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)
                            )
                        }
                        Icon(Icons.Outlined.Settings, "Settings", tint = Color.White, modifier = Modifier.clickable { onNavigateToSettings() })
                        Icon(Icons.Outlined.CheckCircle, "Favorites", tint = Color.White, modifier = Modifier.clickable { })
                        BadgedBox(
                            badge = {
                                if (cartItemCount > 0) {
                                    Badge(containerColor = Color.Red) {
                                        Text(cartItemCount.toString(), color = Color.White)
                                    }
                                }
                            },
                            modifier = Modifier.clickable { onNavigateToCart() }
                        ) {
                            Icon(Icons.Outlined.ShoppingCart, "Cart", tint = Color.White)
                        }
                    }
                }

                // Search Bar
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text(stringResource(R.string.search_products), color = Color(0xFF888888)) },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = "Search icon", tint = Color(0xFF666666)) },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Default.Clear, contentDescription = "Tozalash", tint = Color(0xFF666666))
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    shape = RoundedCornerShape(8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = Color.White,
                        unfocusedContainerColor = Color.White,
                        disabledContainerColor = Color.White,
                        focusedBorderColor = Color.Transparent,
                        unfocusedBorderColor = Color.Transparent,
                        focusedTextColor = Color(0xFF1A1A1A),
                        unfocusedTextColor = Color(0xFF1A1A1A),
                        cursorColor = Color(0xFF9C27B0)
                    ),
                    singleLine = true
                )
            }
        }

        // Single scrollable area — header + products together
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(0.dp)
        ) {
            // Dashboard Cards Row
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Weather Card
                    Card(
                        modifier = Modifier.weight(1f).height(140.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF2196F3)),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(
                            modifier = Modifier.fillMaxSize().padding(16.dp),
                            verticalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(stringResource(R.string.weather), color = Color.White, fontSize = 16.sp)
                                Text("⛅", fontSize = 20.sp)
                            }
                            Text("24°C", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                            Text(stringResource(R.string.partly_cloudy), color = Color.White, fontSize = 14.sp)
                        }
                    }

                    // Marketplace Card
                    Card(
                        modifier = Modifier.weight(1f).height(140.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF00C853)),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(
                            modifier = Modifier.fillMaxSize().padding(16.dp),
                            verticalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(stringResource(R.string.marketplace), color = Color.White, fontSize = 16.sp)
                                Icon(Icons.Default.Star, contentDescription = "Trend", tint = Color.White, modifier = Modifier.size(20.dp))
                            }
                            Text(stringResource(R.string.market_trends), color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            Text(stringResource(R.string.analytics), color = Color.White, fontSize = 14.sp)
                        }
                    }
                }
                Spacer(modifier = Modifier.height(24.dp))
            }

            // Category Section
            item {
                Text("Category", fontSize = 18.sp, color = MaterialTheme.colorScheme.onBackground, fontWeight = FontWeight.SemiBold)
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(androidx.compose.foundation.rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    if (isLoadingCategories) {
                        repeat(5) {
                            Box(modifier = Modifier.width(76.dp).height(80.dp).background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.1f), RoundedCornerShape(12.dp)))
                        }
                    } else if (categories.isEmpty()) {
                        CategoryItem("🥕", "Vegetables") { onNavigateToCategory("vegetables", "Vegetables") }
                        CategoryItem("🍎", "Fruits") { onNavigateToCategory("fruits", "Fruits") }
                        CategoryItem("🥛", "Dairy") { onNavigateToCategory("dairy", "Dairy") }
                        CategoryItem("🥩", "Meat") { onNavigateToCategory("meat", "Meat") }
                    } else {
                        categories.forEach { category ->
                            CategoryItem(
                                emoji = category.icon,
                                title = category.name,
                                isSelected = selectedCategoryId == category.id,
                                onClick = { onNavigateToCategory(category.id, category.name) }
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(24.dp))
            }

            // Online Farmers Section header
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .background(Color(0xFF4CAF50), RoundedCornerShape(percent = 50))
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        "Online Farmers",
                        fontSize = 18.sp,
                        color = MaterialTheme.colorScheme.onBackground,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    if (selectedCategoryId == null) "All Products" else "Category Products",
                    fontSize = 18.sp,
                    color = MaterialTheme.colorScheme.onBackground,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(8.dp))
            }

            // Products
            if (isLoadingProducts) {
                item {
                    Box(modifier = Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else {
                items(products) { product ->
                    ProductCard(
                        product = product,
                        onClick = {
                            scope.launch {
                                try {
                                    NetworkModule.apiService.recordInteraction(
                                        InteractionRequest(product.id, "view")
                                    )
                                } catch (_: Exception) {}
                            }
                        },
                        onAddToCart = { onAddToCart(product) },
                        onSellerClick = onNavigateToSeller
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                }
            }
        }
    }

    if (showLanguageDialog) {
        AlertDialog(
            onDismissRequest = { showLanguageDialog = false },
            title = { Text("Til tanlash", fontWeight = FontWeight.Bold) },
            text = {
                Column {
                    languages.forEach { (code, label) ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    LocaleHelper.setLocale(context, code)
                                    currentLanguage = code
                                    showLanguageDialog = false
                                    (context as? Activity)?.recreate()
                                }
                                .padding(vertical = 12.dp, horizontal = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(label, fontSize = 16.sp)
                            if (currentLanguage == code) {
                                Icon(
                                    Icons.Default.CheckCircle,
                                    contentDescription = null,
                                    tint = Color(0xFF9C27B0),
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                        if (code != languages.last().first) {
                            Divider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.1f))
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showLanguageDialog = false }) {
                    Text("Yopish")
                }
            }
        )
    }
}

@Composable
fun CategoryItem(emoji: String, title: String, isSelected: Boolean = false, onClick: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) Color(0xFFE1BEE7) else MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .width(76.dp)
            .clickable { onClick() }
    ) {
        Column(
            modifier = Modifier.padding(vertical = 16.dp, horizontal = 4.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(emoji, fontSize = 24.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(title, fontSize = 12.sp, color = if (isSelected) Color(0xFF9C27B0) else MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
        }
    }
}
