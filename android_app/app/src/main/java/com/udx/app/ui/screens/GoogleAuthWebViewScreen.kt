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
                                                // Call the backend callback endpoint via Retrofit
                                                // (uses 10.0.2.2 so it reaches the host machine)
                                                val response = NetworkModule.apiService.handleGoogleCallback(code, state)
                                                val location = response.headers()["Location"] ?: ""

                                                when {
                                                    location.contains("token=") -> {
                                                        val token = location
                                                            .substringAfter("token=")
                                                            .substringBefore("&")
                                                        TokenManager.saveToken(token)
                                                        onSuccess()
                                                    }
                                                    location.contains("error=already_registered") -> {
                                                        errorMessage = "This Google account is already registered. Please login instead."
                                                        isLoading = false
                                                    }
                                                    location.contains("error=not_registered") -> {
                                                        errorMessage = "No account found. Please register first."
                                                        isLoading = false
                                                    }
                                                    else -> {
                                                        errorMessage = "Authentication failed. Please try again."
                                                        isLoading = false
                                                    }
                                                }
                                            } catch (e: Exception) {
                                                errorMessage = "Error: ${e.message}"
                                                isLoading = false
                                            }
                                        }
                                        return true // Prevent WebView from following the redirect
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
