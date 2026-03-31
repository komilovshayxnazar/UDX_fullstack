@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Send
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
import com.udx.app.data.TokenManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

// For simplicity, hardcoded WebSocket URL for localhost
private const val WS_URL = "ws://10.0.2.2:8000/ws/chat/room1/"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(onBack: () -> Unit) {
    var messageText by remember { mutableStateOf("") }
    var messages by remember { mutableStateOf(listOf<String>()) }
    var webSocket by remember { mutableStateOf<WebSocket?>(null) }
    val scope = rememberCoroutineScope()
    
    // Connect to WebSocket when the screen is active
    DisposableEffect(Unit) {
        val client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build()
            
        // Use a dummy user_id based on token, or random if guest
        val userId = TokenManager.getToken() ?: "guest_${System.currentTimeMillis()}"
        val request = Request.Builder()
            .url("$WS_URL$userId")
            .build()
            
        val wsListener = object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                // Incoming message
                messages = messages + text
            }
            
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                messages = messages + "Error: Disconnected"
            }
        }
        
        webSocket = client.newWebSocket(request, wsListener)
        
        onDispose {
            webSocket?.close(1000, "Screen closed")
            client.dispatcher.executorService.shutdown()
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF5F5F5))) {
        // Top Header Section
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF9C27B0))
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                }
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        text = "Contract Discussion",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Active",
                        color = Color.White.copy(alpha = 0.8f),
                        fontSize = 14.sp
                    )
                }
            }
        }

        // Chat Messages
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(messages) { msg ->
                // Check if message is mine (starts with my user ID or format)
                val isMine = msg.startsWith((TokenManager.getToken() ?: "guest"))
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = if (isMine) Arrangement.End else Arrangement.Start
                ) {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = if (isMine) Color(0xFF9C27B0) else Color.White,
                        shadowElevation = 1.dp
                    ) {
                        Text(
                            text = if (isMine) msg.substringAfter(":") else msg,
                            color = if (isMine) Color.White else Color.Black,
                            modifier = Modifier.padding(12.dp),
                            fontSize = 16.sp
                        )
                    }
                }
            }
        }

        // Input Field
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = Color.White,
            shadowElevation = 4.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = messageText,
                    onValueChange = { messageText = it },
                    label = { Text(stringResource(R.string.message)) },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(24.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color(0xFFEEEEEE),
                        unfocusedBorderColor = Color(0xFFEEEEEE)
                    )
                )
                Spacer(modifier = Modifier.width(8.dp))
                IconButton(
                    onClick = {
                        if (messageText.isNotBlank()) {
                            webSocket?.send(messageText)
                            messageText = ""
                        }
                    },
                    modifier = Modifier
                        .size(48.dp)
                        .background(Color(0xFF9C27B0), RoundedCornerShape(50))
                ) {
                    Icon(Icons.Default.Send, contentDescription = "Send", tint = Color.White)
                }
            }
        }
    }
}
