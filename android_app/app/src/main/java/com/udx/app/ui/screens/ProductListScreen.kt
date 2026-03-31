@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.ProductRemote
import com.udx.app.data.InteractionRequest
import kotlinx.coroutines.launch
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color

@Composable
fun ProductListScreen(
    onLogout: () -> Unit = {},
    onAddProduct: () -> Unit = {},
    onAddToCart: (ProductRemote) -> Unit = {},
    externalCategoryId: String? = null,
    onCategorySelected: (String?) -> Unit = {}
) {
    var products by remember { mutableStateOf<List<ProductRemote>>(emptyList()) }
    var b2bProducts by remember { mutableStateOf<List<ProductRemote>>(emptyList()) }
    var recommendedProducts by remember { mutableStateOf<List<ProductRemote>>(emptyList()) }
    var categories by remember { mutableStateOf<List<com.udx.app.data.Category>>(emptyList()) }
    var selectedCategoryId by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var isSeller by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun loadProducts() {
        isLoading = true
        error = null
    }

    LaunchedEffect(externalCategoryId) {
        if (externalCategoryId != selectedCategoryId) {
            selectedCategoryId = externalCategoryId
            isLoading = true
        }
    }

    LaunchedEffect(isLoading, selectedCategoryId) {
        if (isLoading) {
            try {
                products = NetworkModule.apiService.getProducts(categoryId = selectedCategoryId)
                if (selectedCategoryId == null) {
                    try {
                        b2bProducts = NetworkModule.apiService.getProducts(isB2b = true)
                    } catch (e: Exception) {
                        b2bProducts = emptyList()
                    }
                    try {
                        recommendedProducts = NetworkModule.apiService.getRecommendations(limit = 10)
                    } catch (e: Exception) {
                        recommendedProducts = emptyList()
                    }
                    try {
                        categories = NetworkModule.apiService.getCategories()
                    } catch (e: Exception) {
                        categories = emptyList()
                    }
                }
                try {
                    val me = NetworkModule.apiService.getMe()
                    isSeller = me.role == "seller"
                } catch (e: Exception) {
                    isSeller = false
                }
                isLoading = false
            } catch (e: Exception) {
                error = e.message ?: "Failed to load products"
                isLoading = false
            }
        }
    }

    Scaffold(
        floatingActionButton = {
            if (isSeller) {
                FloatingActionButton(onClick = onAddProduct) {
                    Icon(Icons.Default.Add, contentDescription = "Add Product")
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                error != null -> {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "⚠️ Could not load products",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Spacer(modifier = Modifier.height(24.dp))
                        Button(onClick = { loadProducts() }) {
                            Text(stringResource(R.string.retry))
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // Category Filter Row
                        if (categories.isNotEmpty()) {
                            item {
                                Text(
                                    "Tags",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(bottom = 8.dp)
                                )
                                LazyRow(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    item {
                                        FilterChip(
                                            selected = selectedCategoryId == null,
                                            onClick = { 
                                                onCategorySelected(null)
                                                selectedCategoryId = null
                                                isLoading = true 
                                            },
                                            label = { Text("All") }
                                        )
                                    }
                                    items(categories) { category ->
                                        FilterChip(
                                            selected = selectedCategoryId == category.id,
                                            onClick = { 
                                                onCategorySelected(category.id)
                                                selectedCategoryId = category.id
                                                isLoading = true
                                            },
                                            label = { Text("${category.icon} ${category.name}") }
                                        )
                                    }
                                }
                                Spacer(modifier = Modifier.height(8.dp))
                            }
                        }

                        // Recommended Section (only when no category is selected)
                        if (recommendedProducts.isNotEmpty() && selectedCategoryId == null) {
                            item {
                                Text(
                                    "🌟 Recommended for You",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(bottom = 8.dp)
                                )
                                LazyRow(
                                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    items(recommendedProducts) { product ->
                                        TrendCard(
                                            product = product,
                                            onClick = {
                                                scope.launch {
                                                    try {
                                                        NetworkModule.apiService.recordInteraction(
                                                            InteractionRequest(product.id, "view")
                                                        )
                                                    } catch (e: Exception) {}
                                                }
                                            },
                                            onAddToCart = { onAddToCart(product) }
                                        )
                                    }
                                }
                                Spacer(modifier = Modifier.height(16.dp))
                            }
                        }

                        // Trend Market Section
                        if (products.isNotEmpty()) {
                            item {
                                Text(
                                    "✨ Trend Market",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(bottom = 8.dp)
                                )
                                LazyRow(
                                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    items(products.take(5)) { product ->
                                        TrendCard(
                                            product = product,
                                            onClick = {
                                                scope.launch {
                                                    try {
                                                        NetworkModule.apiService.recordInteraction(
                                                            InteractionRequest(product.id, "view")
                                                        )
                                                    } catch (e: Exception) {}
                                                }
                                            },
                                            onAddToCart = { onAddToCart(product) }
                                        )
                                    }
                                }
                                Spacer(modifier = Modifier.height(16.dp))
                            }
                        }

                        // B2B Wholesale Market Section (only when no category is selected)
                        if (b2bProducts.isNotEmpty() && selectedCategoryId == null) {
                            item {
                                Text(
                                    "🏢 B2B Wholesale Market",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(bottom = 8.dp, top = 8.dp)
                                )
                                LazyRow(
                                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    items(b2bProducts) { product ->
                                        TrendCard(
                                            product = product,
                                            onClick = {
                                                scope.launch {
                                                    try {
                                                        NetworkModule.apiService.recordInteraction(
                                                            InteractionRequest(product.id, "view")
                                                        )
                                                    } catch (e: Exception) {}
                                                }
                                            },
                                            onAddToCart = { onAddToCart(product) }
                                        )
                                    }
                                }
                                Spacer(modifier = Modifier.height(16.dp))
                            }
                        }

                        if (products.isNotEmpty()) {
                            item {
                                Text(
                                    "All Products",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }

                        items(products) { product ->
                            ProductCard(
                                product = product,
                                onClick = {
                                    scope.launch {
                                        try {
                                            NetworkModule.apiService.recordInteraction(
                                                InteractionRequest(product.id, "view")
                                            )
                                        } catch (e: Exception) {}
                                    }
                                },
                                onAddToCart = { onAddToCart(product) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun TrendCard(product: ProductRemote, onClick: () -> Unit = {}, onAddToCart: () -> Unit = {}) {
    Card(
        modifier = Modifier.width(160.dp).clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column {
            val imageUrl = if (product.image.startsWith("http")) product.image else "http://10.0.2.2:8000${product.image}"
            Box {
                AsyncImage(
                    model = imageUrl,
                    contentDescription = null,
                    modifier = Modifier.height(100.dp).fillMaxWidth(),
                    contentScale = ContentScale.Crop
                )
                IconButton(
                    onClick = onAddToCart,
                    modifier = Modifier.align(Alignment.TopEnd).padding(4.dp).size(24.dp).background(Color.White.copy(alpha = 0.7f), RoundedCornerShape(percent = 50))
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Add to Cart", modifier = Modifier.size(16.dp), tint = Color(0xFF9C27B0))
                }
            }
            Column(modifier = Modifier.padding(8.dp)) {
                Text(product.name, style = MaterialTheme.typography.bodyMedium, maxLines = 1, fontWeight = FontWeight.Bold)
                Text("$${product.price}", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Composable
fun ProductCard(product: ProductRemote, onClick: () -> Unit = {}, onAddToCart: () -> Unit = {}) {
    Card(
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        modifier = Modifier.fillMaxWidth().clickable { onClick() }
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            val imageUrl = if (product.image.startsWith("http")) product.image else "http://10.0.2.2:8000${product.image}"
            AsyncImage(
                model = imageUrl,
                contentDescription = product.name,
                modifier = Modifier.size(80.dp),
                contentScale = ContentScale.Crop
            )

            Spacer(modifier = Modifier.width(16.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = product.name,
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = "$${product.price} / ${product.unit}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.secondary
                )
                Text(
                    text = product.description,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2
                )
            }
            
            IconButton(
                onClick = onAddToCart,
                colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF9C27B0), contentColor = Color.White)
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add to Cart")
            }
        }
    }
}
