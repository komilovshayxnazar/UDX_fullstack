@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
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
import com.udx.app.data.ChatRemote
import com.udx.app.data.MessageRemote
import com.udx.app.data.NetworkModule
import com.udx.app.data.TokenManager
import kotlinx.coroutines.launch
import okhttp3.*
import java.util.concurrent.TimeUnit

private const val WS_BASE = "ws://10.0.2.2:8000/ws/chat"

enum class ConnectionState { CONNECTING, CONNECTED, DISCONNECTED }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(onBack: () -> Unit) {
    var chats by remember { mutableStateOf<List<ChatRemote>>(emptyList()) }
    var selectedChat by remember { mutableStateOf<ChatRemote?>(null) }
    var isLoadingChats by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        try {
            chats = NetworkModule.apiService.getChats()
        } catch (_: Exception) {
        } finally {
            isLoadingChats = false
        }
    }

    if (selectedChat == null) {
        // Chat list screen
        ChatListScreen(
            chats = chats,
            isLoading = isLoadingChats,
            onBack = onBack,
            onSelectChat = { selectedChat = it }
        )
    } else {
        // Individual chat screen
        ChatDetailScreen(
            chat = selectedChat!!,
            onBack = { selectedChat = null }
        )
    }
}

@Composable
fun ChatListScreen(
    chats: List<ChatRemote>,
    isLoading: Boolean,
    onBack: () -> Unit,
    onSelectChat: (ChatRemote) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF9C27B0))
                .padding(16.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.messages),
                    color = Color.White,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        when {
            isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color(0xFF9C27B0))
            }
            chats.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No conversations yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            else -> LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(chats) { chat ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelectChat(chat) },
                        color = MaterialTheme.colorScheme.surface
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Surface(
                                shape = RoundedCornerShape(50),
                                color = Color(0xFF9C27B0),
                                modifier = Modifier.size(48.dp)
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Text(
                                        text = (chat.otherUser.name?.firstOrNull() ?: '?').toString().uppercase(),
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 18.sp
                                    )
                                }
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = chat.otherUser.name ?: "Unknown",
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 16.sp
                                )
                                Text(
                                    text = chat.lastMessage ?: "",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontSize = 14.sp,
                                    maxLines = 1
                                )
                            }
                            if (chat.unreadCount > 0) {
                                Badge(containerColor = Color(0xFF9C27B0)) {
                                    Text(
                                        chat.unreadCount.toString(),
                                        color = Color.White,
                                        fontSize = 12.sp
                                    )
                                }
                            }
                        }
                    }
                    Divider(color = MaterialTheme.colorScheme.outlineVariant, thickness = 0.5.dp)
                }
            }
        }
    }
}

@Composable
fun ChatDetailScreen(chat: ChatRemote, onBack: () -> Unit) {
    var messageText by remember { mutableStateOf("") }
    var messages by remember { mutableStateOf<List<MessageRemote>>(emptyList()) }
    var connectionState by remember { mutableStateOf(ConnectionState.CONNECTING) }
    var webSocket by remember { mutableStateOf<WebSocket?>(null) }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    // Load message history
    LaunchedEffect(chat.id) {
        try {
            messages = NetworkModule.apiService.getChatMessages(chat.id)
        } catch (_: Exception) {}
    }

    // Connect WebSocket with JWT token
    DisposableEffect(chat.id) {
        val token = TokenManager.getToken() ?: run {
            connectionState = ConnectionState.DISCONNECTED
            return@DisposableEffect onDispose {}
        }
        val client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build()
        val request = Request.Builder()
            .url("$WS_BASE/${chat.id}?token=$token")
            .build()

        val ws = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                connectionState = ConnectionState.CONNECTED
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                // Format: "sender_id:message_text"
                val parts = text.split(":", limit = 2)
                val senderId = parts.getOrNull(0) ?: ""
                val body = parts.getOrNull(1) ?: text
                val newMsg = MessageRemote(
                    id = System.currentTimeMillis().toString(),
                    chatId = chat.id,
                    senderId = senderId,
                    text = body,
                    timestamp = null
                )
                messages = messages + newMsg
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                connectionState = ConnectionState.DISCONNECTED
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                connectionState = ConnectionState.DISCONNECTED
            }
        })

        webSocket = ws

        onDispose {
            ws.close(1000, "Screen closed")
            client.dispatcher.executorService.shutdown()
        }
    }

    // Scroll to bottom when new messages arrive
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        // Header
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
                        text = chat.otherUser.name ?: "Chat",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = when (connectionState) {
                            ConnectionState.CONNECTED -> "Active"
                            ConnectionState.CONNECTING -> "Connecting..."
                            ConnectionState.DISCONNECTED -> "Offline"
                        },
                        color = Color.White.copy(alpha = 0.8f),
                        fontSize = 14.sp
                    )
                }
            }
        }

        // Connection warning banner (not a chat bubble)
        if (connectionState == ConnectionState.DISCONNECTED) {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color(0xFFFFF3E0)
            ) {
                Text(
                    text = "Real-time messaging unavailable. Messages sent will still be saved.",
                    color = Color(0xFFE65100),
                    fontSize = 12.sp,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }
        }

        // Messages
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(messages) { msg ->
                val isMine = msg.senderId == TokenManager.getMyId()
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = if (isMine) Arrangement.End else Arrangement.Start
                ) {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = if (isMine) Color(0xFF9C27B0) else MaterialTheme.colorScheme.surface,
                        shadowElevation = 1.dp,
                        modifier = Modifier.widthIn(max = 280.dp)
                    ) {
                        Text(
                            text = msg.text,
                            color = if (isMine) Color.White else MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.padding(12.dp),
                            fontSize = 16.sp
                        )
                    }
                }
            }
        }

        // Input
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
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
                        focusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant
                    ),
                    singleLine = true
                )
                Spacer(modifier = Modifier.width(8.dp))
                IconButton(
                    onClick = {
                        val text = messageText.trim()
                        if (text.isBlank()) return@IconButton
                        messageText = ""
                        scope.launch {
                            try {
                                // Always save via REST (reliable)
                                val saved = NetworkModule.apiService.sendMessage(chat.id, text)
                                if (connectionState != ConnectionState.CONNECTED) {
                                    messages = messages + saved
                                }
                                // Also send via WebSocket for real-time delivery
                                webSocket?.send(text)
                            } catch (_: Exception) {}
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
