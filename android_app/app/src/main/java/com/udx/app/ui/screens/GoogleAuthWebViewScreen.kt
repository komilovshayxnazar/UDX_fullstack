@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.material3.ExperimentalMaterial3Api

import android.annotation.SuppressLint
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.TokenManager
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun GoogleAuthWebViewScreen(
    authUrl: String,
    onSuccess: () -> Unit,
    onCancel: () -> Unit
) {
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.sign_in_google)) },
                navigationIcon = {
                    IconButton(onClick = onCancel) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            AndroidView(
                factory = { context ->
                    WebView(context).apply {
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        settings.userAgentString = "Mozilla/5.0 (Linux; Android 10; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

                        webViewClient = object : WebViewClient() {
                            override fun onPageFinished(view: WebView?, url: String?) {
                                isLoading = false
                            }

                            override fun shouldOverrideUrlLoading(
                                view: WebView?,
                                request: WebResourceRequest?
                            ): Boolean {
                                val url = request?.url?.toString() ?: return false

                                // Intercept the callback before it leaves the app
                                if (url.contains("localhost") && url.contains("/auth/google/callback")) {
                                    val uri = android.net.Uri.parse(url)
                                    val code = uri.getQueryParameter("code")
                                    val state = uri.getQueryParameter("state")

                                    if (code != null) {
                                        isLoading = true
                                        scope.launch {
                                            try {
                                                val response = NetworkModule.apiService.handleGoogleCallback(code, state)
                                                when {
                                                    response.token != null -> {
                                                        TokenManager.saveToken(response.token)
                                                        onSuccess()
                                                    }
                                                    response.error == "already_registered" -> {
                                                        errorMessage = "Bu Google akkaunt allaqachon ro'yxatdan o'tgan. Iltimos, login qiling."
                                                        isLoading = false
                                                    }
                                                    response.error == "not_registered" -> {
                                                        errorMessage = "Akkaunt topilmadi. Iltimos, avval ro'yxatdan o'ting."
                                                        isLoading = false
                                                    }
                                                    else -> {
                                                        errorMessage = "Autentifikatsiya muvaffaqiyatsiz. Qayta urinib ko'ring."
                                                        isLoading = false
                                                    }
                                                }
                                            } catch (e: Exception) {
                                                errorMessage = "Xatolik: ${e.message}"
                                                isLoading = false
                                            }
                                        }
                                        return true
                                    }
                                }
                                return false
                            }
                        }
                        loadUrl(authUrl)
                    }
                },
                modifier = Modifier.fillMaxSize()
            )

            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            }

            if (errorMessage != null) {
                Card(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp)
                        .fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = errorMessage!!,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(onClick = onCancel) { Text("Go Back") }
                    }
                }
            }
        }
    }
}
