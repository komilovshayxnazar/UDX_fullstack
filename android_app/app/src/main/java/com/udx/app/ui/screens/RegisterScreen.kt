@file:OptIn(ExperimentalMaterial3Api::class)

package com.udx.app.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import android.content.Intent
import android.net.Uri
import androidx.compose.ui.platform.LocalContext
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.PhoneOtpInit
import com.udx.app.data.PhoneOtpVerify
import com.udx.app.data.UserCreate
import kotlinx.coroutines.launch
import retrofit2.HttpException

private enum class RegisterStep { INFO, OTP, PASSWORD }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RegisterScreen(
    onRegisterSuccess: () -> Unit,
    onNavigateToLogin: () -> Unit,
    onGoogleRegister: (authUrl: String) -> Unit
) {
    var step by remember { mutableStateOf(RegisterStep.INFO) }

    // Step 1 — INFO
    var name by remember { mutableStateOf("") }
    var phoneNumber by remember { mutableStateOf("") }
    var selectedRole by remember { mutableStateOf("buyer") }

    // Step 2 — OTP (phone-based deep link flow)
    var otpToken by remember { mutableStateOf("") }
    var otpBotUsername by remember { mutableStateOf("udxregister_bot") }
    var deepLinkOpened by remember { mutableStateOf(false) }
    var otpCode by remember { mutableStateOf("") }

    // Step 3 — PASSWORD
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var confirmPasswordVisible by remember { mutableStateOf(false) }

    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val passwordsDontMatch = stringResource(R.string.passwords_dont_match)

    val brush = Brush.verticalGradient(
        colors = listOf(
            MaterialTheme.colorScheme.primaryContainer,
            MaterialTheme.colorScheme.background
        )
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(brush),
        contentAlignment = Alignment.Center
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth(0.9f)
                .padding(16.dp),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 32.dp, horizontal = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = stringResource(R.string.create_account),
                    style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.primary,
                    textAlign = TextAlign.Center
                )

                Text(
                    text = when (step) {
                        RegisterStep.INFO     -> stringResource(R.string.register_step_info)
                        RegisterStep.OTP      -> stringResource(R.string.register_step_otp)
                        RegisterStep.PASSWORD -> stringResource(R.string.register_step_password)
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
                )
                
                // Step Indicators
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 24.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    StepDot(active = step == RegisterStep.INFO || step == RegisterStep.OTP || step == RegisterStep.PASSWORD)
                    Divider(Modifier.width(32.dp).padding(horizontal = 4.dp), color = if (step == RegisterStep.OTP || step == RegisterStep.PASSWORD) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant)
                    StepDot(active = step == RegisterStep.OTP || step == RegisterStep.PASSWORD)
                    Divider(Modifier.width(32.dp).padding(horizontal = 4.dp), color = if (step == RegisterStep.PASSWORD) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant)
                    StepDot(active = step == RegisterStep.PASSWORD)
                }

                AnimatedContent(
                    targetState = step,
                    transitionSpec = {
                        fadeIn() + slideInHorizontally(initialOffsetX = { it }) togetherWith fadeOut() + slideOutHorizontally(targetOffsetX = { -it })
                    },
                    label = "register_steps"
                ) { targetStep ->
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        when (targetStep) {
                            RegisterStep.INFO -> {
                                OutlinedTextField(
                                    value = name,
                                    onValueChange = { name = it },
                                    label = { Text(stringResource(R.string.full_name)) },
                                    leadingIcon = { Icon(Icons.Filled.Person, contentDescription = "Name") },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    shape = RoundedCornerShape(12.dp)
                                )

                                Spacer(modifier = Modifier.height(16.dp))

                                OutlinedTextField(
                                    value = phoneNumber,
                                    onValueChange = { input ->
                                        val filtered = input.filter { it.isDigit() || it == '+' || it == ' ' || it == '-' }
                                        val clean = if (filtered.startsWith("+")) filtered else filtered.replace("+", "")
                                        phoneNumber = clean
                                    },
                                    label = { Text(stringResource(R.string.phone_number)) },
                                    leadingIcon = { Icon(Icons.Filled.Phone, contentDescription = "Phone") },
                                    placeholder = { Text("+998 90 123 45 67") },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    shape = RoundedCornerShape(12.dp),
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone)
                                )

                                Spacer(modifier = Modifier.height(20.dp))

                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceEvenly
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        RadioButton(
                                            selected = selectedRole == "buyer",
                                            onClick = { selectedRole = "buyer" }
                                        )
                                        Text(stringResource(R.string.buyer), style = MaterialTheme.typography.bodyMedium)
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        RadioButton(
                                            selected = selectedRole == "seller",
                                            onClick = { selectedRole = "seller" }
                                        )
                                        Text(stringResource(R.string.seller), style = MaterialTheme.typography.bodyMedium)
                                    }
                                }

                                if (errorMessage != null) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = errorMessage!!,
                                        color = MaterialTheme.colorScheme.error,
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }

                                Spacer(modifier = Modifier.height(24.dp))

                                Button(
                                    onClick = {
                                        errorMessage = null
                                        if (name.isBlank() || phoneNumber.isBlank()) {
                                            errorMessage = "Iltimos, barcha maydonlarni to'ldiring"
                                            return@Button
                                        }
                                        isLoading = true
                                        scope.launch {
                                            try {
                                                val resp = NetworkModule.apiService.initPhoneOtp(
                                                    PhoneOtpInit(phoneNumber)
                                                )
                                                otpToken = resp.token
                                                otpBotUsername = resp.botUsername
                                                deepLinkOpened = false
                                                step = RegisterStep.OTP
                                            } catch (e: Exception) {
                                                errorMessage = e.message ?: "OTP yuborishda xato"
                                            } finally {
                                                isLoading = false
                                            }
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    enabled = !isLoading,
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    if (isLoading) {
                                        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
                                    } else {
                                        Text(stringResource(R.string.continue_btn), fontSize = MaterialTheme.typography.titleMedium.fontSize)
                                    }
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                OutlinedButton(
                                    onClick = {
                                        isLoading = true
                                        errorMessage = null
                                        scope.launch {
                                            try {
                                                val response = NetworkModule.apiService.getGoogleRegisterUrl()
                                                isLoading = false
                                                onGoogleRegister(response.authUrl)
                                            } catch (e: Exception) {
                                                isLoading = false
                                                errorMessage = "Failed to get Google registration URL: ${e.message}"
                                            }
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    enabled = !isLoading,
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    Text(stringResource(R.string.register_google))
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                TextButton(onClick = onNavigateToLogin) {
                                    Text(stringResource(R.string.already_have_account))
                                }
                            }

                            RegisterStep.OTP -> {
                                Text(
                                    text = "Telegram orqali tasdiqlash",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    textAlign = TextAlign.Center
                                )

                                Spacer(modifier = Modifier.height(16.dp))

                                // Step 1: open Telegram deep link
                                Button(
                                    onClick = {
                                        val uri = Uri.parse("tg://resolve?domain=$otpBotUsername&start=$otpToken")
                                        val intent = Intent(Intent.ACTION_VIEW, uri)
                                        context.startActivity(intent)
                                        deepLinkOpened = true
                                    },
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    shape = RoundedCornerShape(12.dp),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = MaterialTheme.colorScheme.secondary
                                    )
                                ) {
                                    Icon(Icons.Filled.Send, contentDescription = null, modifier = Modifier.size(18.dp))
                                    Spacer(Modifier.width(8.dp))
                                    Text("Telegramga o'tish", fontSize = MaterialTheme.typography.titleMedium.fontSize)
                                }

                                if (deepLinkOpened) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = "Telegramdan kelgan 6 xonali kodni kiriting",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        textAlign = TextAlign.Center
                                    )
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                OutlinedTextField(
                                    value = otpCode,
                                    onValueChange = { if (it.length <= 6 && it.all(Char::isDigit)) otpCode = it },
                                    label = { Text(stringResource(R.string.enter_otp_code)) },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                                    shape = RoundedCornerShape(12.dp)
                                )

                                if (errorMessage != null) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = errorMessage!!,
                                        color = MaterialTheme.colorScheme.error,
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                Button(
                                    onClick = {
                                        errorMessage = null
                                        if (otpCode.length != 6) {
                                            errorMessage = "6 xonali kodni kiriting"
                                            return@Button
                                        }
                                        isLoading = true
                                        scope.launch {
                                            try {
                                                NetworkModule.apiService.verifyPhoneOtp(
                                                    PhoneOtpVerify(phoneNumber, otpCode)
                                                )
                                                step = RegisterStep.PASSWORD
                                            } catch (e: HttpException) {
                                                val errorBody = e.response()?.errorBody()?.string()
                                                errorMessage = try {
                                                    org.json.JSONObject(errorBody ?: "").getString("detail")
                                                } catch (_: Exception) { "Noto'g'ri kod" }
                                            } catch (e: Exception) {
                                                errorMessage = e.message ?: "Noto'g'ri kod"
                                            } finally {
                                                isLoading = false
                                            }
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    enabled = !isLoading && otpCode.length == 6,
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    if (isLoading) {
                                        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
                                    } else {
                                        Text(stringResource(R.string.verify), fontSize = MaterialTheme.typography.titleMedium.fontSize)
                                    }
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                TextButton(onClick = {
                                    step = RegisterStep.INFO
                                    otpCode = ""
                                    otpToken = ""
                                    deepLinkOpened = false
                                    errorMessage = null
                                }) {
                                    Text(stringResource(R.string.back))
                                }
                            }

                            RegisterStep.PASSWORD -> {
                                OutlinedTextField(
                                    value = password,
                                    onValueChange = { password = it },
                                    label = { Text(stringResource(R.string.create_password)) },
                                    leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = "Password") },
                                    visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    shape = RoundedCornerShape(12.dp),
                                    trailingIcon = {
                                        IconButton(onClick = { passwordVisible = !passwordVisible }) {
                                            Icon(
                                                imageVector = if (passwordVisible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                                                contentDescription = if (passwordVisible) "Hide password" else "Show password"
                                            )
                                        }
                                    },
                                    supportingText = {
                                        Text(
                                            "Min 8 chars, uppercase, lowercase, digit, special (!@#\$%^&*)",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                )

                                Spacer(modifier = Modifier.height(16.dp))

                                OutlinedTextField(
                                    value = confirmPassword,
                                    onValueChange = { confirmPassword = it },
                                    label = { Text(stringResource(R.string.confirm_password)) },
                                    leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = "Confirm Password") },
                                    visualTransformation = if (confirmPasswordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    shape = RoundedCornerShape(12.dp),
                                    trailingIcon = {
                                        IconButton(onClick = { confirmPasswordVisible = !confirmPasswordVisible }) {
                                            Icon(
                                                imageVector = if (confirmPasswordVisible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                                                contentDescription = if (confirmPasswordVisible) "Hide password" else "Show password"
                                            )
                                        }
                                    }
                                )

                                if (errorMessage != null) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = errorMessage!!,
                                        color = MaterialTheme.colorScheme.error,
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }

                                Spacer(modifier = Modifier.height(24.dp))

                                Button(
                                    onClick = {
                                        errorMessage = null
                                        if (password.length < 8) {
                                            errorMessage = "Password must be at least 8 characters"
                                            return@Button
                                        }
                                        if (!password.any { it.isUpperCase() }) {
                                            errorMessage = "Password must contain an uppercase letter"
                                            return@Button
                                        }
                                        if (!password.any { it.isLowerCase() }) {
                                            errorMessage = "Password must contain a lowercase letter"
                                            return@Button
                                        }
                                        if (!password.any { it.isDigit() }) {
                                            errorMessage = "Password must contain a digit"
                                            return@Button
                                        }
                                        if (!password.any { it in "!@#\$%^&*(),.?\":{}|<>" }) {
                                            errorMessage = "Password must contain a special character (!@#\$%^&*...)"
                                            return@Button
                                        }
                                        if (password != confirmPassword) {
                                            errorMessage = passwordsDontMatch
                                            return@Button
                                        }
                                        isLoading = true
                                        scope.launch {
                                            try {
                                                NetworkModule.apiService.register(
                                                    UserCreate(
                                                        phone = phoneNumber,
                                                        password = password,
                                                        name = name.takeIf { it.isNotBlank() },
                                                        role = selectedRole,
                                                        telegramUsername = null
                                                    )
                                                )
                                                isLoading = false
                                                onRegisterSuccess()
                                            } catch (e: HttpException) {
                                                isLoading = false
                                                val errorBody = e.response()?.errorBody()?.string()
                                                errorMessage = try {
                                                    val json = org.json.JSONObject(errorBody ?: "")
                                                    val detail = json.get("detail")
                                                    if (detail is String) detail
                                                    else {
                                                        val arr = json.getJSONArray("detail")
                                                        arr.getJSONObject(0).getString("msg")
                                                            .removePrefix("Value error, ")
                                                    }
                                                } catch (_: Exception) {
                                                    "Registration failed (${e.code()})"
                                                }
                                            } catch (e: Exception) {
                                                isLoading = false
                                                errorMessage = e.message ?: "Registration failed"
                                            }
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    enabled = !isLoading,
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    if (isLoading) {
                                        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
                                    } else {
                                        Text(stringResource(R.string.create_account), fontSize = MaterialTheme.typography.titleMedium.fontSize)
                                    }
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                TextButton(onClick = {
                                    step = RegisterStep.OTP
                                    errorMessage = null
                                }) {
                                    Text(stringResource(R.string.back))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun StepDot(active: Boolean) {
    Box(
        modifier = Modifier
            .size(12.dp)
            .clip(CircleShape)
            .background(if (active) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant)
    )
}
