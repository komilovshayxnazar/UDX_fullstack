@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import android.content.Context
import androidx.compose.ui.platform.LocalContext
import com.udx.app.utils.CurrencyFormatter
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
import androidx.compose.ui.graphics.Brush
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
    val context = LocalContext.current

    var productsByName by remember { mutableStateOf<Map<String, List<ProductRemote>>>(emptyMap()) }
    var selectedName by remember { mutableStateOf<String?>(null) }
    var priceHistory by remember { mutableStateOf<List<PriceHistory>>(emptyList()) }
    var avgCurrentPrice by remember { mutableStateOf(0.0) }
    var isLoading by remember { mutableStateOf(true) }
    var showDropdown by remember { mutableStateOf(false) }

    val currentCurrency by remember {
        mutableStateOf(
            context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE)
                .getString("currency", "USD") ?: "USD"
        )
    }
    var exchangeRate by remember { mutableStateOf(1.0) }

    // Valyuta kursi — O'zbekiston Markaziy banki
    LaunchedEffect(currentCurrency) {
        if (currentCurrency != "USD") {
            try {
                val (rates, _) = CurrencyFormatter.fetchCbuRates()
                exchangeRate = rates[currentCurrency] ?: 1.0
            } catch (_: Exception) { exchangeRate = 1.0 }
        } else {
            exchangeRate = 1.0
        }
    }

    // Mahsulotlarni yuklash + tanlangan mahsulotning tarixini yuklash — bitta LaunchedEffect
    LaunchedEffect(selectedName) {
        // Birinchi marta: mahsulotlarni yukla
        if (productsByName.isEmpty()) {
            try {
                val all = NetworkModule.apiService.getProducts()
                val grouped = all.groupBy { it.name.trim() }
                productsByName = grouped
                // selectedName hali null — birinchisini tanlaymiz va davom etamiz
                val firstName = grouped.keys.firstOrNull() ?: return@LaunchedEffect
                selectedName = firstName
                // Ushbu LaunchedEffect qayta ishga tushadi selectedName o'zgarganda,
                // shuning uchun bu yerda tarix yuklashni qilmaymiz
                return@LaunchedEffect
            } catch (_: Exception) {
            } finally {
                isLoading = false
            }
        }

        // Tanlangan nom bo'yicha tarix yuklash
        val name = selectedName ?: return@LaunchedEffect
        val group = productsByName[name]
        if (group.isNullOrEmpty()) return@LaunchedEffect

        avgCurrentPrice = group.map { it.price }.average()

        val merged = mutableListOf<PriceHistory>()
        for (product in group) {
            try {
                merged += NetworkModule.apiService.getPriceHistory(product.id)
            } catch (_: Exception) { }
        }
        // Sanaga qarab saralash (ISO string taqqoslash to'g'ri ishlaydi)
        priceHistory = merged.sortedBy { it.date }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(stringResource(R.string.market_trends), fontWeight = FontWeight.Bold, color = Color.White)
                        Text(stringResource(R.string.real_time_market_data), fontSize = 12.sp, color = Color.White.copy(alpha = 0.8f))
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
                    CircularProgressIndicator(color = Color(0xFF9C27B0))
                }
            } else {
                // Karta 1: Mahsulot tanlash va joriy narx
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        // Dropdown — faqat unique nomlar
                        Box {
                            OutlinedButton(
                                onClick = { showDropdown = true },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(selectedName ?: stringResource(R.string.all_categories), color = MaterialTheme.colorScheme.onSurface)
                                Spacer(Modifier.weight(1f))
                                Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = MaterialTheme.colorScheme.onSurface)
                            }
                            DropdownMenu(
                                expanded = showDropdown,
                                onDismissRequest = { showDropdown = false }
                            ) {
                                productsByName.keys.sorted().forEach { name ->
                                    DropdownMenuItem(
                                        text = { Text(name) },
                                        onClick = {
                                            if (name != selectedName) {
                                                priceHistory = emptyList()
                                                selectedName = name
                                            }
                                            showDropdown = false
                                        }
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        val latestPrice = priceHistory.lastOrNull()?.price ?: avgCurrentPrice
                        val trendColor: Color
                        val trendStr: String

                        if (priceHistory.size >= 2) {
                            val current = priceHistory.last().price
                            val previous = priceHistory[priceHistory.size - 2].price
                            val diff = if (previous > 0) ((current - previous) / previous) * 100 else 0.0
                            trendColor = if (diff >= 0) Color(0xFF4CAF50) else Color(0xFFF44336)
                            trendStr = if (diff >= 0) "+${String.format("%.2f", diff)}%" else "${String.format("%.2f", diff)}%"
                        } else {
                            trendColor = Color.Gray
                            trendStr = "—"
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = CurrencyFormatter.formatPrice(latestPrice, currentCurrency, exchangeRate),
                                style = MaterialTheme.typography.headlineMedium,
                                color = Color(0xFF9C27B0),
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = trendColor.copy(alpha = 0.12f)
                            ) {
                                Text(
                                    text = trendStr,
                                    color = trendColor,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            stringResource(R.string.latest_price_data),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                // Karta 2: Narxlar tarixi grafigi
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    modifier = Modifier.fillMaxWidth().height(260.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp).fillMaxSize()) {
                        Text(
                            stringResource(R.string.price_history),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        if (priceHistory.isEmpty()) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                CircularProgressIndicator(color = Color(0xFF9C27B0), modifier = Modifier.size(32.dp))
                            }
                        } else {
                            PriceChart(priceHistory = priceHistory, modifier = Modifier.fillMaxSize())
                        }
                    }
                }

                // Karta 3: Market Insights
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(stringResource(R.string.market_insights), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(16.dp))

                        val maxPrice = priceHistory.maxOfOrNull { it.price } ?: avgCurrentPrice
                        val minPrice = priceHistory.minOfOrNull { it.price } ?: avgCurrentPrice
                        val avgPrice = if (priceHistory.isNotEmpty()) priceHistory.map { it.price }.average() else avgCurrentPrice

                        InsightRow(stringResource(R.string.all_time_high), CurrencyFormatter.formatPrice(maxPrice, currentCurrency, exchangeRate), Color(0xFF4CAF50))
                        Spacer(modifier = Modifier.height(12.dp))
                        InsightRow(stringResource(R.string.all_time_low), CurrencyFormatter.formatPrice(minPrice, currentCurrency, exchangeRate), Color(0xFFF44336))
                        Spacer(modifier = Modifier.height(12.dp))
                        InsightRow(stringResource(R.string.average_price), CurrencyFormatter.formatPrice(avgPrice, currentCurrency, exchangeRate), Color(0xFF9C27B0))
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))
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
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 16.sp)
        Text(value, color = valueColor, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
    }
}

@Composable
fun PriceChart(priceHistory: List<PriceHistory>, modifier: Modifier = Modifier) {
    if (priceHistory.isEmpty()) return

    // "2026-03-13T17:47:54.342000" → "Mar 13" formatiga o'girish
    val dateParser = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
    val dateFormatter = SimpleDateFormat("MMM d", Locale.getDefault())

    val prices = priceHistory.map { it.price.toFloat() }
    val rawMax = prices.maxOrNull() ?: 1f
    val rawMin = prices.minOrNull() ?: 0f
    val padding = (rawMax - rawMin) * 0.15f  // 15% padding yuqori-pastdan
    val chartMax = rawMax + padding
    val chartMin = (rawMin - padding).coerceAtLeast(0f)
    val priceRange = (chartMax - chartMin).let { if (it == 0f) 1f else it }

    val purple = Color(0xFF9C27B0)

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val leftPad = 52f    // Y labels uchun
        val bottomPad = 30f  // X labels uchun
        val chartW = w - leftPad
        val chartH = h - bottomPad

        // --- Y grid + labels ---
        val ySteps = 4
        for (i in 0..ySteps) {
            val ratio = i.toFloat() / ySteps
            val y = chartH - ratio * chartH
            val price = chartMin + ratio * priceRange

            drawLine(
                color = Color.LightGray.copy(alpha = 0.4f),
                start = Offset(leftPad, y),
                end = Offset(w, y),
                strokeWidth = 1f
            )
            drawContext.canvas.nativeCanvas.drawText(
                String.format("%.2f", price),
                0f,
                y + 9f,
                android.graphics.Paint().apply {
                    color = android.graphics.Color.GRAY
                    textSize = 22f
                    isAntiAlias = true
                }
            )
        }

        if (prices.size < 2) return@Canvas

        // --- Nuqta koordinatalari ---
        val xStep = chartW / (prices.size - 1).toFloat()
        val points = prices.mapIndexed { i, price ->
            val x = leftPad + i * xStep
            val y = chartH - ((price - chartMin) / priceRange) * chartH
            Offset(x, y)
        }

        // --- Gradient fill ---
        val fillPath = Path().apply {
            moveTo(points.first().x, chartH)
            points.forEach { lineTo(it.x, it.y) }
            lineTo(points.last().x, chartH)
            close()
        }
        drawPath(
            path = fillPath,
            brush = Brush.verticalGradient(
                colors = listOf(purple.copy(alpha = 0.25f), purple.copy(alpha = 0.0f)),
                startY = 0f,
                endY = chartH
            )
        )

        // --- Chiziq ---
        val linePath = Path().apply {
            moveTo(points.first().x, points.first().y)
            points.drop(1).forEach { lineTo(it.x, it.y) }
        }
        drawPath(linePath, color = purple, style = Stroke(width = 3.5f))

        // --- X labels (faqat 6 ta) ---
        val labelIndices = when {
            prices.size <= 6 -> prices.indices.toList()
            else -> {
                val step = (prices.size - 1) / 5
                (0..5).map { (it * step).coerceAtMost(prices.size - 1) }
            }
        }
        labelIndices.forEach { i ->
            val dateStr = try {
                val iso = priceHistory[i].date.take(10) // "2026-03-13"
                val d = dateParser.parse(iso)
                if (d != null) dateFormatter.format(d) else "—"
            } catch (_: Exception) { "—" }

            drawContext.canvas.nativeCanvas.drawText(
                dateStr,
                points[i].x - 18f,
                h,
                android.graphics.Paint().apply {
                    color = android.graphics.Color.GRAY
                    textSize = 22f
                    isAntiAlias = true
                }
            )
        }

        // --- Nuqtalar ---
        points.forEachIndexed { i, point ->
            // Faqat label nuqtalarida yoki oxirgisida
            if (i in labelIndices || i == prices.size - 1) {
                drawCircle(color = Color.White, radius = 7f, center = point)
                drawCircle(color = purple, radius = 5f, center = point)
            }
        }
    }
}
