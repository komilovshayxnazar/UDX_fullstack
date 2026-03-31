@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.udx.app.R
import com.udx.app.data.ContractRemote
import com.udx.app.data.NetworkModule

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContractsScreen(onBack: () -> Unit) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedFilter by remember { mutableStateOf("All") }
    var contracts by remember { mutableStateOf<List<ContractRemote>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    val filters = listOf("All", "Active", "Pending", "Completed")

    // Fetch contracts for the current user only
    LaunchedEffect(Unit) {
        try {
            contracts = NetworkModule.apiService.getContracts()
        } catch (e: Exception) {
            errorMessage = "Could not load contracts"
        } finally {
            isLoading = false
        }
    }

    val filteredContracts = contracts.filter { contract ->
        val matchesFilter = selectedFilter == "All" ||
                contract.status.equals(selectedFilter, ignoreCase = true)
        val matchesSearch = searchQuery.isBlank() ||
                contract.title.contains(searchQuery, ignoreCase = true) ||
                contract.buyerName?.contains(searchQuery, ignoreCase = true) == true ||
                contract.sellerName?.contains(searchQuery, ignoreCase = true) == true
        matchesFilter && matchesSearch
    }

    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF5F5F5))) {
        // Top Header Section (Purple Background)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF9C27B0))
                .padding(top = 16.dp, bottom = 16.dp, start = 16.dp, end = 16.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(
                                text = stringResource(R.string.contracts),
                                color = Color.White,
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "${filteredContracts.size} contract${if (filteredContracts.size != 1) "s" else ""}",
                                color = Color.White.copy(alpha = 0.8f),
                                fontSize = 14.sp
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Search Bar
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text(stringResource(R.string.search_contracts), color = Color.White.copy(alpha = 0.7f)) },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = "Search", tint = Color.White.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth().height(50.dp),
                    shape = RoundedCornerShape(8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = Color(0xFFAA47BC),
                        unfocusedContainerColor = Color(0xFFAA47BC),
                        disabledContainerColor = Color(0xFFAA47BC),
                        focusedBorderColor = Color.Transparent,
                        unfocusedBorderColor = Color.Transparent,
                        cursorColor = Color.White,
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White
                    ),
                    singleLine = true
                )
            }
        }

        // Filters Section
        LazyRow(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White)
                .padding(vertical = 12.dp, horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(filters) { filter ->
                val isSelected = selectedFilter == filter
                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = if (isSelected) Color(0xFFb451fc) else Color(0xFFF5F6F8),
                    modifier = Modifier.clickable { selectedFilter = filter }
                ) {
                    Text(
                        text = filter,
                        color = if (isSelected) Color.White else Color.DarkGray,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        Divider(color = Color(0xFFEEEEEE), thickness = 1.dp)

        when {
            isLoading -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = Color(0xFF9C27B0))
                }
            }
            errorMessage != null -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(errorMessage ?: "", color = Color.Gray)
                }
            }
            filteredContracts.isEmpty() -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(stringResource(R.string.no_contracts_found), color = Color.Gray, fontSize = 16.sp)
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredContracts) { contract ->
                        val statusColor = when (contract.status.lowercase()) {
                            "active" -> Color(0xFF4CAF50)
                            "pending" -> Color(0xFFFFA000)
                            "completed" -> Color(0xFF2196F3)
                            "cancelled" -> Color(0xFFF44336)
                            else -> Color.Gray
                        }
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(contract.title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                    Text(
                                        text = contract.status.replaceFirstChar { it.uppercase() },
                                        color = statusColor,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                                Spacer(modifier = Modifier.height(8.dp))
                                if (contract.buyerName != null) {
                                    Text("Buyer: ${contract.buyerName}", color = Color.Gray, fontSize = 14.sp)
                                }
                                if (contract.sellerName != null) {
                                    Text("Seller: ${contract.sellerName}", color = Color.Gray, fontSize = 14.sp)
                                }
                                Text("Amount: $${String.format("%.2f", contract.amount)}", color = Color.Gray, fontSize = 14.sp)
                                if (!contract.description.isNullOrBlank()) {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(contract.description, color = Color.Gray, fontSize = 13.sp)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
