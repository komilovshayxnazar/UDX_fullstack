package com.udx.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.udx.app.data.NetworkModule
import com.udx.app.data.PublicUserProfile
import com.udx.app.data.ReviewRemote

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SellerProfileScreen(sellerId: String, onBack: () -> Unit) {
    var profile by remember { mutableStateOf<PublicUserProfile?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(sellerId) {
        try {
            profile = NetworkModule.apiService.getPublicProfile(sellerId)
        } catch (e: Exception) {
            error = e.message
        } finally {
            isLoading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(profile?.name ?: "Profil") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Ortga")
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
        when {
            isLoading -> Box(Modifier.fillMaxSize().padding(padding), Alignment.Center) {
                CircularProgressIndicator()
            }
            error != null -> Box(Modifier.fillMaxSize().padding(padding), Alignment.Center) {
                Text("Profil topilmadi", color = MaterialTheme.colorScheme.error)
            }
            profile != null -> {
                val p = profile!!
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Avatar + ism + holat
                    item {
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            elevation = CardDefaults.cardElevation(4.dp)
                        ) {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(20.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Box(contentAlignment = Alignment.BottomEnd) {
                                    if (p.avatar != null) {
                                        val url = if (p.avatar.startsWith("http")) p.avatar
                                                  else "http://10.0.2.2:8000${p.avatar}"
                                        AsyncImage(
                                            model = url,
                                            contentDescription = null,
                                            modifier = Modifier.size(80.dp).clip(RoundedCornerShape(percent = 50)),
                                            contentScale = ContentScale.Crop
                                        )
                                    } else {
                                        Box(
                                            modifier = Modifier.size(80.dp)
                                                .background(Color(0xFF9C27B0), RoundedCornerShape(percent = 50)),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Text(
                                                (p.name?.firstOrNull()?.uppercaseChar() ?: '?').toString(),
                                                color = Color.White, fontSize = 32.sp, fontWeight = FontWeight.Bold
                                            )
                                        }
                                    }
                                    if (p.isOnline) {
                                        Box(
                                            modifier = Modifier.size(18.dp).padding(2.dp)
                                                .background(Color(0xFF4CAF50), RoundedCornerShape(percent = 50))
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    Text(p.name ?: "Noma'lum", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                                    if (p.isVerified) {
                                        Icon(Icons.Default.VerifiedUser, contentDescription = "Tasdiqlangan",
                                            tint = Color(0xFF2196F3), modifier = Modifier.size(18.dp))
                                    }
                                }

                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Icon(Icons.Default.Star, contentDescription = null,
                                        tint = Color(0xFFFFC107), modifier = Modifier.size(16.dp))
                                    Text("%.1f".format(p.rating), fontWeight = FontWeight.SemiBold)
                                    Text("(${p.reviewCount} sharh)", color = Color.Gray, fontSize = 13.sp)
                                }

                                if (!p.description.isNullOrBlank()) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(p.description, style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                                }

                                if (p.isVerified) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Surface(
                                        shape = RoundedCornerShape(20.dp),
                                        color = Color(0xFFE3F2FD)
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            Icon(Icons.Default.VerifiedUser, contentDescription = null,
                                                tint = Color(0xFF2196F3), modifier = Modifier.size(14.dp))
                                            Text("Tasdiqlangan sotuvchi", color = Color(0xFF2196F3), fontSize = 12.sp)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Savdo statistikasi
                    item {
                        Text("Savdo statistikasi", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            StatCard(
                                modifier = Modifier.weight(1f),
                                icon = Icons.Default.ShoppingBag,
                                label = "Jami",
                                value = "${p.totalOrders}",
                                color = Color(0xFF9C27B0)
                            )
                            StatCard(
                                modifier = Modifier.weight(1f),
                                icon = Icons.Default.CheckCircle,
                                label = "Muvaffaqiyatli",
                                value = "${p.successfulOrders}",
                                color = Color(0xFF4CAF50)
                            )
                            StatCard(
                                modifier = Modifier.weight(1f),
                                icon = Icons.Default.Cancel,
                                label = "Bekor qilingan",
                                value = "${p.unsuccessfulOrders}",
                                color = Color(0xFFF44336)
                            )
                            StatCard(
                                modifier = Modifier.weight(1f),
                                icon = Icons.Default.Pending,
                                label = "Jarayonda",
                                value = "${p.inProgressOrders}",
                                color = Color(0xFFFF9800)
                            )
                        }
                    }

                    // Sharhlar
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Xaridorlar sharhlari", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            if (p.reviews.isNotEmpty()) {
                                Text("${p.reviews.size} ta", color = Color.Gray, fontSize = 13.sp)
                            }
                        }
                    }

                    if (p.reviews.isEmpty()) {
                        item {
                            Box(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("Hali sharh yo'q", color = Color.Gray)
                            }
                        }
                    } else {
                        items(p.reviews) { review ->
                            ReviewCard(review)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatCard(
    modifier: Modifier = Modifier,
    icon: ImageVector,
    label: String,
    value: String,
    color: Color
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.08f)),
        elevation = CardDefaults.cardElevation(0.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(22.dp))
            Text(value, fontWeight = FontWeight.Bold, fontSize = 18.sp, color = color)
            Text(label, fontSize = 10.sp, color = color.copy(alpha = 0.8f),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
private fun ReviewCard(review: ReviewRemote) {
    Card(
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Box(
                        modifier = Modifier.size(28.dp)
                            .background(Color(0xFF9C27B0).copy(alpha = 0.15f), RoundedCornerShape(percent = 50)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            (review.reviewerName?.firstOrNull()?.uppercaseChar() ?: '?').toString(),
                            fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF9C27B0)
                        )
                    }
                    Column {
                        Text(review.reviewerName ?: "Foydalanuvchi",
                            fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        if (review.isVerifiedPurchase) {
                            Text("✓ Tasdiqlangan xarid", fontSize = 10.sp, color = Color(0xFF4CAF50))
                        }
                    }
                }
                // Yulduzlar
                Row {
                    repeat(5) { i ->
                        Icon(
                            if (i < review.rating) Icons.Default.Star else Icons.Default.StarBorder,
                            contentDescription = null,
                            tint = Color(0xFFFFC107),
                            modifier = Modifier.size(14.dp)
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(review.comment, style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface)
        }
    }
}
