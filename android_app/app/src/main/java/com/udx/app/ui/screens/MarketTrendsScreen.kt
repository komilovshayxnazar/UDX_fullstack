@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.PriceHistory
import com.udx.app.data.ProductRemote
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MarketTrendsScreen(onBack: () -> Unit) {
    var products by remember { mutableStateOf<List<ProductRemote>>(emptyList()) }
    var selectedProduct by remember { mutableStateOf<ProductRemote?>(null) }
    var priceHistory by remember { mutableStateOf<List<PriceHistory>>(emptyList()) }
    
    var isLoading by remember { mutableStateOf(true) }
    
    var showDropdown by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        try {
            products = NetworkModule.apiService.getProducts()
            if (products.isNotEmpty()) {
                selectedProduct = products.first()
            }
        } catch (e: Exception) {
            // Handle error
        } finally {
            isLoading = false
        }
    }
    
    LaunchedEffect(selectedProduct) {
        selectedProduct?.let { product ->
            try {
                priceHistory = NetworkModule.apiService.getPriceHistory(product.id)
            } catch (e: Exception) {
                priceHistory = emptyList()
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Column {
                        Text(stringResource(R.string.market_trends), fontWeight = FontWeight.Bold, color = Color.White)
                        Text(stringResource(R.string.real_time_market_data), fontSize = 12.sp, color = Color.White.copy(alpha=0.8f))
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF9C27B0))
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            if (isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                // Top Card: Product Selector & Current Trend
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        // Dropdown
                        Box {
                            OutlinedButton(
                                onClick = { showDropdown = true },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(selectedProduct?.name ?: "Select Product", color = Color.Black)
                                Spacer(Modifier.weight(1f))
                                Icon(Icons.Default.ArrowDropDown, contentDescription = "Dropdown", tint = Color.Black)
                            }
                            DropdownMenu(
                                expanded = showDropdown,
                                onDismissRequest = { showDropdown = false }
                            ) {
                                products.forEach { product ->
                                    DropdownMenuItem(
                                        text = { Text(product.name) },
                                        onClick = {
                                            selectedProduct = product
                                            showDropdown = false
                                        }
                                    )
                                }
                            }
                        }
                        
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        // Price & Trend Display
                        val latestPrice = priceHistory.lastOrNull()?.price ?: selectedProduct?.price ?: 0.0
                        var trendStr = "0.00%"
                        var trendColor = Color.Gray
                        
                        if (priceHistory.size >= 2) {
                            val current = priceHistory.last().price
                            val previous = priceHistory[priceHistory.size - 2].price
                            if (previous > 0) {
                                val diff = ((current - previous) / previous) * 100
                                trendStr = String.format("%.2f%%", diff)
                                trendColor = if (diff >= 0) Color(0xFF4CAF50) else Color(0xFFF44336)
                                if (diff > 0) trendStr = "+$trendStr"
                            }
                        }
                        
                        Row(verticalAlignment = Alignment.Bottom) {
                            Text(
                                text = "$${String.format("%.2f", latestPrice)}",
                                style = MaterialTheme.typography.headlineMedium,
                                color = Color(0xFF9C27B0),
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.width(16.dp))
                            Text(
                                text = trendStr,
                                style = MaterialTheme.typography.titleMedium,
                                color = trendColor,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(stringResource(R.string.latest_price_data), style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                    }
                }


                // Middle Card: Price History Chart
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    modifier = Modifier.fillMaxWidth().height(250.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp).fillMaxSize()) {
                        Text(stringResource(R.string.price_history), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        if (priceHistory.isEmpty()) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text(stringResource(R.string.no_history_data), color = Color.Gray)
                            }
                        } else {
                            PriceChart(priceHistory = priceHistory, modifier = Modifier.fillMaxSize())
                        }
                    }
                }

                // Bottom Card: Market Insights
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(stringResource(R.string.market_insights), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(16.dp))

                        val maxPrice = priceHistory.maxOfOrNull { it.price } ?: selectedProduct?.price ?: 0.0
                        val minPrice = priceHistory.minOfOrNull { it.price } ?: selectedProduct?.price ?: 0.0
                        val avgPrice = if (priceHistory.isNotEmpty()) priceHistory.map { it.price }.average() else selectedProduct?.price ?: 0.0

                        InsightRow(stringResource(R.string.all_time_high), String.format("$%.2f", maxPrice), Color(0xFF4CAF50))
                        Spacer(modifier = Modifier.height(12.dp))
                        InsightRow(stringResource(R.string.all_time_low), String.format("$%.2f", minPrice), Color(0xFFF44336))
                        Spacer(modifier = Modifier.height(12.dp))
                        InsightRow(stringResource(R.string.average_price), String.format("$%.2f", avgPrice), Color(0xFF9C27B0))
                    }
                }

                Spacer(modifier = Modifier.height(32.dp)) // padding for bottom nav

            }
        }
    }
}

@Composable
fun InsightRow(label: String, value: String, valueColor: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = Color.Gray, fontSize = 16.sp)
        Text(value, color = valueColor, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
    }
}

@Composable
fun PriceChart(priceHistory: List<PriceHistory>, modifier: Modifier = Modifier) {
    if (priceHistory.isEmpty()) return
    
    // Simply to format the dates. Real world we might parse ISO 8601
    val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
    val formatter = SimpleDateFormat("MMM d", Locale.getDefault())
    
    val prices = priceHistory.map { it.price.toFloat() }
    val maxPrice = (prices.maxOrNull() ?: 10f) * 1.2f // Add 20% breathing room
    val minPrice = 0f // Start Y axis from 0 for simplicity
    
    Canvas(modifier = modifier) {
        val width = size.width
        val height = size.height
        val padding = 40f
        
        val drawingWidth = width - padding
        val drawingHeight = height - padding
        
        // Draw Y axis Grid Lines
        val steps = 5
        for (i in 0..steps) {
            val y = drawingHeight - (i * drawingHeight / steps)
            val value = minPrice + (maxPrice - minPrice) * i / steps
            
            drawLine(
                color = Color.LightGray.copy(alpha = 0.5f),
                start = Offset(padding, y),
                end = Offset(width, y),
                strokeWidth = 1f
            )
            
            drawContext.canvas.nativeCanvas.drawText(
                String.format("%.0f", value),
                0f,
                y + 10f,
                android.graphics.Paint().apply {
                    color = android.graphics.Color.GRAY
                    textSize = 24f
                }
            )
        }
        
        if (prices.isEmpty()) return@Canvas

        // Draw X Axis dates and Data Points
        val xStep = if (prices.size > 1) drawingWidth / (prices.size - 1).toFloat() else drawingWidth / 2f
        
        val points = mutableListOf<Offset>()
        for (i in prices.indices) {
            val x = if (prices.size > 1) padding + (i * xStep) else padding + xStep
            
            val priceRange = maxPrice - minPrice
            val safeRange = if (priceRange == 0f) 1f else priceRange
            val y = drawingHeight - ((prices[i] - minPrice) / safeRange * drawingHeight)
            
            points.add(Offset(x, y))
            
            // Try formatting date
            var dateStr = "Date ${i+1}"
            try {
                if (i >= 0 && i < priceHistory.size) {
                    val dateObj = parser.parse(priceHistory[i].date)
                    if (dateObj != null) {
                        dateStr = formatter.format(dateObj)
                    }
                }
            } catch (e: Exception) { }
            
            // Safe calculation for skip step to prevent index exceptions
            val labelCount = prices.size
            val skipStep = if (labelCount > 5) labelCount / 5 else 1
            
            // Draw X Axis labels
            if (labelCount <= 5 || i % skipStep == 0 || i == labelCount - 1) {
                drawContext.canvas.nativeCanvas.drawText(
                    dateStr,
                    x - 20f,
                    height,
                    android.graphics.Paint().apply {
                        color = android.graphics.Color.GRAY
                        textSize = 24f
                    }
                )
            }
        }
        
        // Draw Line connecting points
        if (points.size > 1) {
            val path = Path()
            path.moveTo(points.first().x, points.first().y)
            for (i in 1 until points.size) {
                path.lineTo(points[i].x, points[i].y)
            }
            drawPath(
                path = path,
                color = Color(0xFF9C27B0), // Purple line
                style = Stroke(width = 4f)
            )
        } else if (points.size == 1) {
             // Draw a simple line spanning the middle for a single point
             val path = Path()
             path.moveTo(padding, points.first().y)
             path.lineTo(width, points.first().y)
             drawPath(
                path = path,
                color = Color(0xFF9C27B0).copy(alpha=0.3f), 
                style = Stroke(width = 4f)
            )
        }
        
        // Draw circles on points
        for (point in points) {
            drawCircle(
                color = Color(0xFF9C27B0),
                radius = 6f,
                center = point
            )
        }
    }
}
