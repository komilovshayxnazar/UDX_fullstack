package com.udx.app.ui.screens

import android.net.Uri
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.udx.app.R
import com.udx.app.data.NetworkModule
import com.udx.app.data.PasswordUpdate
import com.udx.app.data.TokenManager
import com.udx.app.data.User
import com.udx.app.data.UserUpdate
import com.udx.app.data.TransactionRequest
import com.udx.app.utils.LocaleHelper
import com.udx.app.utils.CurrencyFormatter
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.HttpException
import java.io.File
import java.io.FileOutputStream

fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

val ALL_CURRENCIES = linkedMapOf(
    "UZS" to "O'zbek so'mi (so'm)",
    "USD" to "US Dollar ($)",
    "EUR" to "Euro (€)",
    "RUB" to "Russian Ruble (₽)",
    "KZT" to "Kazakhstan Tenge (₸)",
    "KGS" to "Kyrgyzstan Som (с)",
    "TJS" to "Tajikistan Somoni (SM)",
    "TMT" to "Turkmenistan Manat (T)",
    "AZN" to "Azerbaijan Manat (₼)",
    "GEL" to "Georgian Lari (₾)",
    "AMD" to "Armenian Dram (֏)",
    "UAH" to "Ukrainian Hryvnia (₴)",
    "BYN" to "Belarusian Ruble (Br)",
    "GBP" to "Pound Sterling (£)",
    "CHF" to "Swiss Franc (Fr)",
    "JPY" to "Japan Yen (¥)",
    "CNY" to "Chinese Yuan (¥)",
    "KRW" to "Korean Won (₩)",
    "TRY" to "Turkish Lira (₺)",
    "SAR" to "Saudi Riyal (﷼)",
    "AED" to "UAE Dirham (د.إ)",
    "QAR" to "Qatari Riyal (﷼)",
    "KWD" to "Kuwaiti Dinar (د.ك)",
    "BHD" to "Bahraini Dinar (BD)",
    "INR" to "Indian Rupee (₹)",
    "PKR" to "Pakistan Rupee (₨)",
    "BDT" to "Bangladesh Taka (৳)",
    "IDR" to "Indonesian Rupiah (Rp)",
    "MYR" to "Malaysian Ringgit (RM)",
    "SGD" to "Singapore Dollar (S\$)",
    "THB" to "Thai Baht (฿)",
    "VND" to "Vietnamese Dong (₫)",
    "PHP" to "Philippine Peso (₱)",
    "HKD" to "Hong Kong Dollar (HK\$)",
    "CAD" to "Canadian Dollar (CA\$)",
    "AUD" to "Australian Dollar (A\$)",
    "NZD" to "New Zealand Dollar (NZ\$)",
    "MXN" to "Mexican Peso (MX\$)",
    "BRL" to "Brazilian Real (R\$)",
    "ZAR" to "South African Rand (R)",
    "NOK" to "Norwegian Krone (kr)",
    "SEK" to "Swedish Krona (kr)",
    "DKK" to "Danish Krone (kr)",
    "PLN" to "Polish Zloty (zł)",
    "CZK" to "Czech Koruna (Kč)",
    "HUF" to "Hungarian Forint (Ft)",
    "RON" to "Romanian Leu (lei)",
    "BGN" to "Bulgarian Lev (лв)",
    "ILS" to "Israeli Shekel (₪)",
    "EGP" to "Egyptian Pound (E£)",
    "MAD" to "Moroccan Dirham (MAD)",
    "DZD" to "Algerian Dinar (DA)",
    "IQD" to "Iraqi Dinar (ع.د)",
    "YER" to "Yemeni Rial (﷼)",
    "JOD" to "Jordanian Dinar (JD)",
    "OMR" to "Omani Rial (﷼)",
    "LBP" to "Lebanese Pound (L£)",
    "SYP" to "Syrian Pound (S£)",
    "MNT" to "Mongolian Tugrik (₮)",
    "AFN" to "Afghan Afghani (؋)",
    "MMK" to "Myanmar Kyat (K)",
    "KHR" to "Cambodian Riel (៛)",
    "LAK" to "Lao Kip (₭)",
    "IRR" to "Iranian Rial (﷼)",
    "MDL" to "Moldovan Leu (L)",
    "RSD" to "Serbian Dinar (din)",
    "CUP" to "Cuban Peso (CUP)",
    "UYU" to "Uruguayan Peso (\$U)",
    "ARS" to "Argentine Peso (AR\$)",
    "VES" to "Venezuelan Bolívar (Bs)",
    "BND" to "Brunei Dollar (B\$)",
    "ISK" to "Iceland Krona (kr)",
    "SDG" to "Sudanese Pound (SDG)",
    "LYD" to "Libyan Dinar (LD)",
    "TND" to "Tunisian Dinar (DT)",
    "XDR" to "SDR (XDR)"
)

@Composable
fun ProfileScreen(onLogout: () -> Unit) {
    var userData by remember { mutableStateOf<User?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var showBalanceDialog by remember { mutableStateOf<String?>(null) }
    var showPaymentDetailsDialog by remember { mutableStateOf(false) }
    var showEditProfileDialog by remember { mutableStateOf(false) }
    var showChangePasswordDialog by remember { mutableStateOf(false) }
    var savedCards by remember { mutableStateOf<List<com.udx.app.data.PaymentCard>>(emptyList()) }
    var balanceVisible by remember { mutableStateOf(false) }
    var isUploadingPhoto by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia(),
        onResult = { uri ->
            if (uri != null) {
                isUploadingPhoto = true
                scope.launch {
                    try {
                        val inputStream = context.contentResolver.openInputStream(uri)
                        val tempFile = File(context.cacheDir, "avatar_upload.jpg")
                        FileOutputStream(tempFile).use { out -> inputStream?.copyTo(out) }
                        inputStream?.close()

                        val requestFile = tempFile.asRequestBody("image/*".toMediaTypeOrNull())
                        val body = MultipartBody.Part.createFormData("file", tempFile.name, requestFile)
                        val uploaded = NetworkModule.apiService.uploadImage(body)

                        val updated = NetworkModule.apiService.updateMe(UserUpdate(avatar = uploaded.url))
                        userData = updated
                    } catch (_: Exception) {
                    } finally {
                        isUploadingPhoto = false
                    }
                }
            }
        }
    )

    var pushNotifications by remember { mutableStateOf(true) }
    var messagesFromSellers by remember { mutableStateOf(true) }
    var priceChangesOrders by remember { mutableStateOf(true) }
    var marketNewsAnalytics by remember { mutableStateOf(false) }
    var systemNotifications by remember { mutableStateOf(true) }
    var twoFactorEnabled by remember { mutableStateOf(false) }
    var profilePublic by remember { mutableStateOf(true) }
    var showLanguageDialog by remember { mutableStateOf(false) }
    var currentLangCode by remember { mutableStateOf(LocaleHelper.getLanguage(context)) }
    var showCurrencyDialog by remember { mutableStateOf(false) }
    var showRegionDialog by remember { mutableStateOf(false) }
    var showUnitsDialog by remember { mutableStateOf(false) }

    var currentCurrency by remember {
        mutableStateOf(context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE).getString("currency", "USD") ?: "USD")
    }

    // O'zbekiston Markaziy banki kurslari (base: USD)
    var exchangeRates by remember { mutableStateOf<Map<String, Double>>(mapOf("USD" to 1.0)) }
    var ratesDate by remember { mutableStateOf("") }
    var ratesLoading by remember { mutableStateOf(false) }
    var ratesError by remember { mutableStateOf(false) }

    suspend fun fetchRates() {
        ratesLoading = true
        ratesError = false
        try {
            val (rates, date) = CurrencyFormatter.fetchCbuRates()
            exchangeRates = rates
            ratesDate = date
        } catch (_: Exception) {
            ratesError = true
        } finally {
            ratesLoading = false
        }
    }

    var currentRegion by remember {
        mutableStateOf(context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE).getString("region", "Global") ?: "Global")
    }

    var currentUnit by remember {
        mutableStateOf(context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE).getString("unit", "kg") ?: "kg")
    }

    val languages = linkedMapOf(
        "uz" to "O'zbek",
        "ru" to "Русский",
        "en" to "English",
        "kk" to "Қазақша",
        "ky" to "Кыргызча",
        "tg" to "Тоҷикӣ",
        "de" to "Deutsch",
        "es" to "Español",
        "fr" to "Français"
    )

    val currencies = ALL_CURRENCIES

    val regions = mapOf(
        "Global" to "Global",
        "Uzbekistan" to "Uzbekistan",
        "Kazakhstan" to "Kazakhstan",
        "Kyrgyzstan" to "Kyrgyzstan",
        "Tajikistan" to "Tajikistan",
        "Russia" to "Russia"
    )

    fun loadProfile() {
        scope.launch {
            try {
                val me = NetworkModule.apiService.getMe()
                userData = me
                profilePublic = me.isPublic
            } catch (e: Exception) { } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadProfile()
        try { savedCards = NetworkModule.apiService.getCards() } catch (_: Exception) {}
        fetchRates()
    }

    if (isLoading) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
    ) {
        // ── Header / Avatar ─────────────────────────────────────────────────
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.surface)
                .padding(24.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    modifier = Modifier
                        .size(90.dp)
                        .clip(CircleShape)
                        .clickable {
                            photoPickerLauncher.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                            )
                        },
                    contentAlignment = Alignment.Center
                ) {
                    val avatarUrl = userData?.avatar
                    if (avatarUrl != null) {
                        val fullUrl = if (avatarUrl.startsWith("http")) avatarUrl else "http://10.0.2.2:8000$avatarUrl"
                        AsyncImage(
                            model = fullUrl,
                            contentDescription = "Profile photo",
                            modifier = Modifier.fillMaxSize().clip(CircleShape),
                            contentScale = ContentScale.Crop
                        )
                    } else {
                        Box(
                            modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.primaryContainer),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Person,
                                contentDescription = null,
                                modifier = Modifier.size(52.dp),
                                tint = Color(0xFF9C27B0)
                            )
                        }
                    }
                    // Camera overlay at bottom-right
                    Box(
                        modifier = Modifier
                            .size(26.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF9C27B0))
                            .align(Alignment.BottomEnd),
                        contentAlignment = Alignment.Center
                    ) {
                        if (isUploadingPhoto) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = Color.White,
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.CameraAlt,
                                contentDescription = "Change photo",
                                tint = Color.White,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = userData?.name ?: stringResource(R.string.guest_user),
                    fontWeight = FontWeight.Bold,
                    fontSize = 20.sp
                )
                Text(
                    text = if (userData != null) userData?.role?.replaceFirstChar { it.uppercase() } ?: "" else stringResource(R.string.guest_mode),
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(16.dp))
                // Balance card
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(stringResource(R.string.your_balance), fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        val usdBalance = userData?.balance ?: 0.0
                        val rate = exchangeRates[currentCurrency] ?: 1.0
                        val convertedBalance = usdBalance * rate

                        // Formatlash: UZS uchun alohida, boshqalar uchun 2 xonali
                        val formattedBalance = when {
                            !balanceVisible -> "••••••"
                            else -> CurrencyFormatter.formatPrice(usdBalance, currentCurrency, rate)
                        }

                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Text(
                                formattedBalance,
                                fontSize = 28.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF9C27B0)
                            )
                            IconButton(onClick = { balanceVisible = !balanceVisible }) {
                                Icon(
                                    imageVector = if (balanceVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                    contentDescription = if (balanceVisible) "Hide balance" else "Show balance",
                                    tint = Color(0xFF9C27B0)
                                )
                            }
                        }
                        if (balanceVisible && currentCurrency != "USD") {
                            val rateHint = if (currentCurrency == "UZS")
                                "1 USD = ${java.text.NumberFormat.getNumberInstance(java.util.Locale("ru")).format(rate.toLong())} so'm"
                            else
                                "1 USD = ${String.format("%.2f", rate)} $currentCurrency"
                            Text(rateHint, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        if (userData != null) {
                            Spacer(modifier = Modifier.height(12.dp))
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(
                                    onClick = { showBalanceDialog = "deposit" },
                                    modifier = Modifier.weight(1f),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9C27B0))
                                ) { Text(stringResource(R.string.fill_balance), fontSize = 13.sp) }
                                OutlinedButton(
                                    onClick = { showBalanceDialog = "withdraw" },
                                    modifier = Modifier.weight(1f)
                                ) { Text(stringResource(R.string.withdraw), fontSize = 13.sp) }
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Account & Security ───────────────────────────────────────────────
        SettingsSectionHeader(stringResource(R.string.account_security))
        SettingsGroup {
            SettingsItem(
                icon = Icons.Default.Person,
                iconBg = Color(0xFF9C27B0),
                title = stringResource(R.string.edit_profile),
                subtitle = stringResource(R.string.edit_profile_sub),
                onClick = { showEditProfileDialog = true }
            )
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.Phone,
                iconBg = Color(0xFF9C27B0),
                title = stringResource(R.string.phone_number),
                subtitle = if (userData?.phone?.startsWith("google_") == true) "Google account" else userData?.phone ?: stringResource(R.string.not_set),
                subtitleColor = if (userData?.phone == null) Color(0xFFE53935) else Color.Unspecified
            )
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.Lock,
                iconBg = Color(0xFF9C27B0),
                title = stringResource(R.string.change_password),
                onClick = { showChangePasswordDialog = true }
            )
            SettingsDivider()
            // 2FA toggle
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF9C27B0).copy(alpha = 0.12f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.Lock, contentDescription = null, tint = Color(0xFF9C27B0), modifier = Modifier.size(20.dp))
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(stringResource(R.string.two_factor_auth), fontSize = 15.sp, fontWeight = FontWeight.Medium)
                }
                Switch(
                    checked = twoFactorEnabled,
                    onCheckedChange = { twoFactorEnabled = it },
                    colors = SwitchDefaults.colors(checkedThumbColor = Color(0xFF9C27B0), checkedTrackColor = Color(0xFFCE93D8))
                )
            }
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.Star,
                iconBg = Color(0xFF9C27B0),
                title = stringResource(R.string.payment_details),
                subtitle = if (savedCards.isEmpty()) stringResource(R.string.payment_details_sub) else "${savedCards.size} card(s) saved",
                onClick = { showPaymentDetailsDialog = true }
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Notifications ────────────────────────────────────────────────────
        SettingsSectionHeader(stringResource(R.string.notifications))
        SettingsGroup {
            SettingsToggle(icon = Icons.Default.Notifications, iconBg = Color(0xFF1565C0), title = stringResource(R.string.push_notifications), checked = pushNotifications, onCheckedChange = { pushNotifications = it })
            SettingsDivider()
            SettingsToggle(icon = Icons.Default.MailOutline, iconBg = Color(0xFF1565C0), title = stringResource(R.string.messages_from_sellers), checked = messagesFromSellers, onCheckedChange = { messagesFromSellers = it })
            SettingsDivider()
            SettingsToggle(icon = Icons.Default.Star, iconBg = Color(0xFF1565C0), title = stringResource(R.string.price_changes_orders), checked = priceChangesOrders, onCheckedChange = { priceChangesOrders = it })
            SettingsDivider()
            SettingsToggle(icon = Icons.Default.Star, iconBg = Color(0xFF1565C0), title = stringResource(R.string.market_news_analytics), checked = marketNewsAnalytics, onCheckedChange = { marketNewsAnalytics = it })
            SettingsDivider()
            SettingsToggle(icon = Icons.Default.Info, iconBg = Color(0xFF1565C0), title = stringResource(R.string.system_notifications), checked = systemNotifications, onCheckedChange = { systemNotifications = it })
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Privacy ──────────────────────────────────────────────────────────
        SettingsSectionHeader(stringResource(R.string.privacy))
        SettingsGroup {
            SettingsToggle(
                icon = Icons.Default.Person,
                iconBg = Color(0xFF2E7D32),
                title = stringResource(R.string.profile_visibility),
                checked = profilePublic,
                onCheckedChange = { newValue ->
                    profilePublic = newValue
                    scope.launch {
                        try {
                            NetworkModule.apiService.updateMe(UserUpdate(isPublic = newValue))
                        } catch (_: Exception) {
                            // Revert on failure
                            profilePublic = !newValue
                        }
                    }
                }
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Preferences ──────────────────────────────────────────────────────
        SettingsSectionHeader(stringResource(R.string.preferences))
        SettingsGroup {
            val themeState = com.udx.app.ui.theme.LocalThemeState.current
            SettingsToggle(
                icon = Icons.Default.DarkMode,
                iconBg = Color(0xFF37474F),
                title = "Dark Mode",
                checked = themeState.isDark,
                onCheckedChange = { themeState.toggle() }
            )
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.Translate,
                iconBg = Color(0xFF00796B),
                title = stringResource(R.string.language),
                subtitle = languages[currentLangCode] ?: currentLangCode.uppercase(),
                onClick = { showLanguageDialog = true }
            )
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.List,
                iconBg = Color(0xFF00796B),
                title = stringResource(R.string.units_of_measurement),
                subtitle = currentUnit,
                onClick = { showUnitsDialog = true }
            )
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.Home, 
                iconBg = Color(0xFF00796B), 
                title = stringResource(R.string.currency), 
                subtitle = currentCurrency,
                onClick = { showCurrencyDialog = true }
            )
            SettingsDivider()
            SettingsItem(
                icon = Icons.Default.LocationOn, 
                iconBg = Color(0xFF00796B), 
                title = stringResource(R.string.product_search_region), 
                subtitle = regions[currentRegion] ?: "Global",
                onClick = { showRegionDialog = true }
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── About the App ────────────────────────────────────────────────────
        SettingsSectionHeader(stringResource(R.string.about_app))
        SettingsGroup {
            SettingsItem(icon = Icons.Default.Info, iconBg = Color(0xFFE65100), title = stringResource(R.string.help_support), subtitle = "Chat, FAQ")
            SettingsDivider()
            SettingsItem(icon = Icons.Default.Settings, iconBg = Color(0xFF37474F), title = stringResource(R.string.terms_use))
            SettingsDivider()
            SettingsItem(icon = Icons.Default.Lock, iconBg = Color(0xFF37474F), title = stringResource(R.string.privacy_policy))
            SettingsDivider()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF37474F).copy(alpha = 0.12f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.Info, contentDescription = null, tint = Color(0xFF37474F), modifier = Modifier.size(20.dp))
                }
                Spacer(modifier = Modifier.width(12.dp))
                Text(stringResource(R.string.app_version), fontSize = 15.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
                Text("v1.0.0", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // ── Log Out ──────────────────────────────────────────────────────────
        Button(
            onClick = {
                TokenManager.clearToken()
                onLogout()
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .height(52.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE53935)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.Default.ExitToApp, contentDescription = null, tint = Color.White)
            Spacer(modifier = Modifier.width(8.dp))
            Text(stringResource(R.string.log_out), color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        }

        Spacer(modifier = Modifier.height(32.dp))
    }

    // Balance Dialog (deposit / withdraw)
    if (showBalanceDialog != null) {
        var balanceAmount by remember { mutableStateOf("") }
        var selectedCardId by remember { mutableStateOf(savedCards.firstOrNull()?.id ?: "") }
        var balanceError by remember { mutableStateOf<String?>(null) }
        var balanceLoading by remember { mutableStateOf(false) }
        val isDeposit = showBalanceDialog == "deposit"

        AlertDialog(
            onDismissRequest = { if (!balanceLoading) showBalanceDialog = null },
            title = { Text(if (isDeposit) stringResource(R.string.fill_balance) else stringResource(R.string.withdraw)) },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    if (savedCards.isEmpty()) {
                        Text(
                            "No payment cards saved. Add a card in Payment Details first.",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    } else {
                        Text("Select card", style = MaterialTheme.typography.labelMedium)
                        Spacer(modifier = Modifier.height(6.dp))
                        savedCards.forEach { card ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { selectedCardId = card.id }
                                    .padding(vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                RadioButton(
                                    selected = selectedCardId == card.id,
                                    onClick = { selectedCardId = card.id }
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Text("${card.cardType} •••• ${card.last4}", style = MaterialTheme.typography.bodyMedium)
                                    Text("${card.ownerName}  ${card.expiry}", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                        val dialogRate = exchangeRates[currentCurrency] ?: 1.0
                        val currencyLabel = if (currentCurrency == "UZS") "so'm" else currentCurrency
                        OutlinedTextField(
                            value = balanceAmount,
                            onValueChange = { v -> if (v.all { it.isDigit() || it == '.' }) balanceAmount = v },
                            label = { Text("${stringResource(R.string.amount)} ($currencyLabel)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Decimal)
                        )
                        // USD ekvivalenti ko'rsatish
                        if (currentCurrency != "USD") {
                            val enteredAmt = balanceAmount.toDoubleOrNull() ?: 0.0
                            val usdEquiv = if (dialogRate > 0) enteredAmt / dialogRate else 0.0
                            Text(
                                "≈ $${String.format("%.2f", usdEquiv)} USD",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(top = 4.dp)
                            )
                        }
                    }
                    if (balanceError != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(balanceError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (savedCards.isEmpty()) { showBalanceDialog = null; return@Button }
                        val enteredAmount = balanceAmount.toDoubleOrNull()
                        if (enteredAmount == null || enteredAmount <= 0) { balanceError = "Enter a valid amount"; return@Button }
                        if (selectedCardId.isBlank()) { balanceError = "Select a card"; return@Button }
                        // API har doim USD qabul qiladi — tanlangan valyutadan konvert qilamiz
                        val dialogRate2 = exchangeRates[currentCurrency] ?: 1.0
                        val amount = if (currentCurrency == "USD" || dialogRate2 <= 0) enteredAmount
                                     else enteredAmount / dialogRate2
                        balanceLoading = true
                        balanceError = null
                        // Generate idempotency key once per button tap — prevents double charge
                        // if the user taps twice or the network retries the request.
                        val idempotencyKey = java.util.UUID.randomUUID().toString()
                        scope.launch {
                            // Retry up to 3 times with exponential backoff for network failures
                            val maxRetries = 3
                            var attempt = 0
                            var lastError: Exception? = null
                            while (attempt < maxRetries) {
                                try {
                                    if (isDeposit) {
                                        // Same idempotency key on every retry — server deduplicates
                                        NetworkModule.apiService.depositBalance(
                                            TransactionRequest(amount, selectedCardId),
                                            idempotencyKey
                                        )
                                    } else {
                                        NetworkModule.apiService.withdrawBalance(
                                            TransactionRequest(amount, selectedCardId)
                                        )
                                    }
                                    loadProfile()
                                    showBalanceDialog = null
                                    lastError = null
                                    break
                                } catch (e: HttpException) {
                                    // 4xx = hard error, do not retry
                                    val body = e.response()?.errorBody()?.string()
                                    balanceError = try {
                                        val json = org.json.JSONObject(body ?: "")
                                        val d = json.get("detail"); if (d is String) d else "Error"
                                    } catch (_: Exception) { "Failed (${e.code()})" }
                                    break
                                } catch (e: Exception) {
                                    // Network / timeout — retry with backoff
                                    lastError = e
                                    attempt++
                                    if (attempt < maxRetries) {
                                        kotlinx.coroutines.delay(500L * (1L shl (attempt - 1))) // 500ms, 1s, 2s
                                    }
                                }
                            }
                            if (lastError != null) {
                                balanceError = "Network error after $maxRetries attempts. Please try again."
                            }
                            balanceLoading = false
                        }
                    },
                    enabled = !balanceLoading
                ) {
                    if (balanceLoading) CircularProgressIndicator(modifier = Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                    else Text(stringResource(R.string.confirm))
                }
            },
            dismissButton = {
                TextButton(onClick = { showBalanceDialog = null }, enabled = !balanceLoading) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }

    // Language Dialog
    if (showLanguageDialog) {
        AlertDialog(
            onDismissRequest = { showLanguageDialog = false },
            title = { Text(stringResource(R.string.language), fontWeight = FontWeight.Bold) },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    languages.forEach { (code, name) ->
                        val isSelected = currentLangCode == code
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    LocaleHelper.setLocale(context, code)
                                    currentLangCode = code
                                    showLanguageDialog = false
                                    context.findActivity()?.recreate()
                                }
                                .background(
                                    if (isSelected) MaterialTheme.colorScheme.primaryContainer
                                    else Color.Transparent
                                )
                                .padding(vertical = 12.dp, horizontal = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                name,
                                fontSize = 16.sp,
                                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                                color = if (isSelected) MaterialTheme.colorScheme.primary
                                        else MaterialTheme.colorScheme.onSurface
                            )
                            if (isSelected) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                        if (code != languages.keys.last()) {
                            Divider(color = MaterialTheme.colorScheme.outlineVariant)
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showLanguageDialog = false }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }

    // Currency Dialog
    if (showCurrencyDialog) {
        AlertDialog(
            onDismissRequest = { showCurrencyDialog = false },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(stringResource(R.string.currency), modifier = Modifier.weight(1f))
                    IconButton(
                        onClick = { scope.launch { fetchRates() } },
                        enabled = !ratesLoading
                    ) {
                        if (ratesLoading) {
                            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh rates", tint = Color(0xFF9C27B0))
                        }
                    }
                }
            },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    if (ratesDate.isNotEmpty()) {
                        Text(
                            "O'zbekiston MBdan · $ratesDate · Base: USD",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                    }
                    if (ratesError) {
                        Text("Failed to load rates. Tap ↻ to retry.", fontSize = 12.sp, color = Color(0xFFE53935))
                        Spacer(modifier = Modifier.height(8.dp))
                    }
                    currencies.forEach { (code, name) ->
                        val rate = exchangeRates[code]
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE)
                                        .edit()
                                        .putString("currency", code)
                                        .apply()
                                    currentCurrency = code
                                    showCurrencyDialog = false
                                }
                                .background(if (currentCurrency == code) MaterialTheme.colorScheme.primaryContainer else Color.Transparent)
                                .padding(horizontal = 4.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(name, fontSize = 15.sp, modifier = Modifier.weight(1f))
                            val rateText = when {
                                ratesLoading -> "…"
                                code == "USD" -> "Base"
                                rate == null -> "N/A"
                                code == "UZS" -> "1 USD = ${java.text.NumberFormat.getNumberInstance(java.util.Locale("ru")).format(rate.toLong())} so'm"
                                code == "JPY" || code == "KRW" || code == "IDR" ->
                                    "1 USD = ${String.format("%.0f", rate)} $code"
                                else -> "1 USD = ${String.format("%.2f", rate)} $code"
                            }
                            Text(
                                rateText,
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        if (code != currencies.keys.last()) Divider(color = MaterialTheme.colorScheme.outlineVariant)
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showCurrencyDialog = false }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }

    // Region Dialog
    if (showRegionDialog) {
        AlertDialog(
            onDismissRequest = { showRegionDialog = false },
            title = { Text(stringResource(R.string.product_search_region)) },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    regions.forEach { (code, name) ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE)
                                        .edit()
                                        .putString("region", code)
                                        .apply()
                                    currentRegion = code
                                    showRegionDialog = false
                                }
                                .padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(name, fontSize = 16.sp)
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showRegionDialog = false }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }

    // Units of Measurement Dialog
    if (showUnitsDialog) {
        val units = listOf(
            "kg" to "Kilogram (kg)",
            "g" to "Gram (g)",
            "ton" to "Ton (ton)",
            "lb" to "Pound (lb)",
            "oz" to "Ounce (oz)",
            "l" to "Liter (l)",
            "ml" to "Milliliter (ml)",
            "m" to "Meter (m)",
            "cm" to "Centimeter (cm)",
            "m²" to "Square Meter (m²)",
            "m³" to "Cubic Meter (m³)",
            "pcs" to "Pieces (pcs)",
            "box" to "Box",
            "pack" to "Pack"
        )
        AlertDialog(
            onDismissRequest = { showUnitsDialog = false },
            title = { Text(stringResource(R.string.units_of_measurement)) },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    units.forEach { (code, label) ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    context.getSharedPreferences("udx_prefs", Context.MODE_PRIVATE)
                                        .edit()
                                        .putString("unit", code)
                                        .apply()
                                    currentUnit = code
                                    showUnitsDialog = false
                                }
                                .padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(label, fontSize = 16.sp)
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showUnitsDialog = false }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }

    // Payment Details Dialog
    if (showPaymentDetailsDialog) {
        var showAddCard by remember { mutableStateOf(false) }
        var cardNumber by remember { mutableStateOf(TextFieldValue("")) }
        var cardExpiry by remember { mutableStateOf("") }
        var cardOwner by remember { mutableStateOf("") }
        var cardError by remember { mutableStateOf<String?>(null) }
        var cardLoading by remember { mutableStateOf(false) }
        var transactions by remember { mutableStateOf<List<com.udx.app.data.TransactionRecord>>(emptyList()) }

        LaunchedEffect(Unit) {
            try { transactions = NetworkModule.apiService.getTransactions() } catch (_: Exception) {}
        }

        AlertDialog(
            onDismissRequest = { if (!cardLoading) showPaymentDetailsDialog = false },
            title = { Text(stringResource(R.string.payment_details)) },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    if (savedCards.isEmpty() && !showAddCard) {
                        Text("No cards saved yet.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        Spacer(modifier = Modifier.height(8.dp))
                    }
                    savedCards.forEach { card ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFF3E5F5))
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text("${card.cardType} •••• ${card.last4}", fontWeight = FontWeight.SemiBold)
                                    Text("${card.ownerName}  ${card.expiry}", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                                }
                                IconButton(onClick = {
                                    scope.launch {
                                        try {
                                            NetworkModule.apiService.deleteCard(card.id)
                                            savedCards = NetworkModule.apiService.getCards()
                                        } catch (_: Exception) {}
                                    }
                                }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Remove", tint = Color(0xFFE53935))
                                }
                            }
                        }
                    }
                    // Transaction history
                    if (transactions.isNotEmpty() && !showAddCard) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Transaction History", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                        Spacer(modifier = Modifier.height(6.dp))
                        transactions.take(10).forEach { txn ->
                            val isDeposit = txn.type == "deposit"
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = if (isDeposit) Icons.Default.KeyboardArrowDown else Icons.Default.KeyboardArrowUp,
                                    contentDescription = null,
                                    tint = if (isDeposit) Color(0xFF2E7D32) else Color(0xFFE53935),
                                    modifier = Modifier.size(20.dp)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        if (isDeposit) "Deposit" else "Withdraw",
                                        style = MaterialTheme.typography.bodySmall,
                                        fontWeight = FontWeight.Medium
                                    )
                                    Text(txn.transactionId, style = MaterialTheme.typography.labelSmall, color = Color.Gray)
                                }
                                Text(
                                    "${if (isDeposit) "+" else "-"}$${String.format("%.2f", txn.amount)}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = if (isDeposit) Color(0xFF2E7D32) else Color(0xFFE53935),
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }

                    if (showAddCard) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Add new card", style = MaterialTheme.typography.titleSmall)
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = cardNumber,
                            onValueChange = { newValue ->
                                val digits = newValue.text.replace(" ", "").filter(Char::isDigit).take(16)
                                val formatted = digits.chunked(4).joinToString(" ")
                                // cursor pozitsiyasini to'g'ri hisoblash
                                val rawCursor = newValue.selection.end
                                val digitsBeforeCursor = newValue.text.take(rawCursor).replace(" ", "").filter(Char::isDigit).length
                                val spacesBeforeCursor = (digitsBeforeCursor - 1) / 4
                                val newCursor = (digitsBeforeCursor + spacesBeforeCursor).coerceAtMost(formatted.length)
                                cardNumber = TextFieldValue(formatted, TextRange(newCursor))
                            },
                            label = { Text("Card number") },
                            placeholder = { Text("1234 5678 9012 3456") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = cardExpiry,
                                onValueChange = {
                                    val digits = it.replace("/", "").filter(Char::isDigit).take(4)
                                    cardExpiry = if (digits.length >= 3) "${digits.take(2)}/${digits.drop(2)}" else digits
                                },
                                label = { Text("MM/YY") },
                                modifier = Modifier.weight(1f),
                                singleLine = true,
                                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                            )
                            OutlinedTextField(
                                value = cardOwner,
                                onValueChange = { cardOwner = it },
                                label = { Text("Owner name") },
                                modifier = Modifier.weight(2f),
                                singleLine = true
                            )
                        }
                        if (cardError != null) {
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(cardError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(
                                onClick = {
                                    cardError = null
                                    val digits = cardNumber.text.replace(" ", "")
                                    if (digits.length != 16) { cardError = "Enter a 16-digit card number"; return@Button }
                                    if (!cardExpiry.matches(Regex("\\d{2}/\\d{2}"))) { cardError = "Enter expiry as MM/YY"; return@Button }
                                    if (cardOwner.isBlank()) { cardError = "Enter the owner name"; return@Button }

                                    cardLoading = true
                                    scope.launch {
                                        try {
                                            // Step 1: tokenize — gateway returns card_token, full PAN stays client-side
                                            val tokenized = NetworkModule.apiService.tokenizeCard(
                                                com.udx.app.data.CardTokenizeRequest(digits, cardExpiry, cardOwner)
                                            )
                                            // Step 2: save token to our server — PAN never transmitted
                                            val added = NetworkModule.apiService.addCard(
                                                com.udx.app.data.PaymentCardCreate(
                                                    cardToken = tokenized.cardToken,
                                                    last4 = tokenized.last4,
                                                    expiry = tokenized.expiry,
                                                    ownerName = tokenized.ownerName,
                                                    cardType = tokenized.cardType
                                                )
                                            )
                                            savedCards = savedCards + added
                                            cardNumber = TextFieldValue(""); cardExpiry = ""; cardOwner = ""
                                            showAddCard = false
                                        } catch (e: HttpException) {
                                            val body = e.response()?.errorBody()?.string()
                                            cardError = try {
                                                val json = org.json.JSONObject(body ?: "")
                                                val d = json.get("detail")
                                                if (d is String) d
                                                else json.getJSONArray("detail").getJSONObject(0).getString("msg").removePrefix("Value error, ")
                                            } catch (_: Exception) { "Failed (${e.code()})" }
                                        } catch (e: Exception) {
                                            cardError = e.message ?: "Failed to add card"
                                        } finally {
                                            cardLoading = false
                                        }
                                    }
                                },
                                enabled = !cardLoading
                            ) {
                                if (cardLoading) CircularProgressIndicator(modifier = Modifier.size(18.dp), color = MaterialTheme.colorScheme.onPrimary)
                                else Text("Save card")
                            }
                            TextButton(onClick = { showAddCard = false; cardError = null }) { Text(stringResource(R.string.cancel)) }
                        }
                    }
                }
            },
            confirmButton = {
                if (!showAddCard) {
                    Button(onClick = { showAddCard = true }) { Text("+ Add card") }
                }
            },
            dismissButton = {
                TextButton(onClick = { showPaymentDetailsDialog = false }, enabled = !cardLoading) {
                    Text("Close")
                }
            }
        )
    }

    // Edit Profile Dialog
    if (showEditProfileDialog) {
        var editName by remember { mutableStateOf(userData?.name ?: "") }
        var editError by remember { mutableStateOf<String?>(null) }
        var editLoading by remember { mutableStateOf(false) }

        AlertDialog(
            onDismissRequest = { if (!editLoading) showEditProfileDialog = false },
            title = { Text(stringResource(R.string.edit_profile)) },
            text = {
                Column {
                    OutlinedTextField(
                        value = editName,
                        onValueChange = { editName = it },
                        label = { Text(stringResource(R.string.full_name)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    if (editError != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(editError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (editName.isBlank()) { editError = "Name cannot be empty"; return@Button }
                        editLoading = true
                        editError = null
                        scope.launch {
                            try {
                                val updated = NetworkModule.apiService.updateMe(UserUpdate(name = editName))
                                userData = updated
                                showEditProfileDialog = false
                            } catch (e: HttpException) {
                                val body = e.response()?.errorBody()?.string()
                                editError = try {
                                    val json = org.json.JSONObject(body ?: "")
                                    val d = json.get("detail")
                                    if (d is String) d else json.getJSONArray("detail").getJSONObject(0).getString("msg")
                                } catch (_: Exception) { "Update failed (${e.code()})" }
                            } catch (e: Exception) {
                                editError = e.message ?: "Update failed"
                            } finally {
                                editLoading = false
                            }
                        }
                    },
                    enabled = !editLoading
                ) {
                    if (editLoading) CircularProgressIndicator(modifier = Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                    else Text(stringResource(R.string.confirm))
                }
            },
            dismissButton = {
                TextButton(onClick = { showEditProfileDialog = false }, enabled = !editLoading) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }

    // Change Password Dialog
    if (showChangePasswordDialog) {
        var currentPw by remember { mutableStateOf("") }
        var newPw by remember { mutableStateOf("") }
        var confirmPw by remember { mutableStateOf("") }
        var currentPwVisible by remember { mutableStateOf(false) }
        var newPwVisible by remember { mutableStateOf(false) }
        var confirmPwVisible by remember { mutableStateOf(false) }
        var pwError by remember { mutableStateOf<String?>(null) }
        var pwLoading by remember { mutableStateOf(false) }
        var pwSuccess by remember { mutableStateOf(false) }

        AlertDialog(
            onDismissRequest = { if (!pwLoading) showChangePasswordDialog = false },
            title = { Text(stringResource(R.string.change_password)) },
            text = {
                Column {
                    if (pwSuccess) {
                        Text("Password changed successfully!", color = MaterialTheme.colorScheme.primary)
                    } else {
                        OutlinedTextField(
                            value = currentPw,
                            onValueChange = { currentPw = it },
                            label = { Text("Current password") },
                            visualTransformation = if (currentPwVisible) VisualTransformation.None else PasswordVisualTransformation(),
                            trailingIcon = {
                                IconButton(onClick = { currentPwVisible = !currentPwVisible }) {
                                    Icon(
                                        imageVector = if (currentPwVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                        contentDescription = null
                                    )
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = newPw,
                            onValueChange = { newPw = it },
                            label = { Text("New password") },
                            visualTransformation = if (newPwVisible) VisualTransformation.None else PasswordVisualTransformation(),
                            trailingIcon = {
                                IconButton(onClick = { newPwVisible = !newPwVisible }) {
                                    Icon(
                                        imageVector = if (newPwVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                        contentDescription = null
                                    )
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            supportingText = { Text("Min 8 chars, uppercase, lowercase, digit, special", style = MaterialTheme.typography.labelSmall) }
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = confirmPw,
                            onValueChange = { confirmPw = it },
                            label = { Text("Confirm new password") },
                            visualTransformation = if (confirmPwVisible) VisualTransformation.None else PasswordVisualTransformation(),
                            trailingIcon = {
                                IconButton(onClick = { confirmPwVisible = !confirmPwVisible }) {
                                    Icon(
                                        imageVector = if (confirmPwVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                        contentDescription = null
                                    )
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        if (pwError != null) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(pwError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            },
            confirmButton = {
                if (pwSuccess) {
                    Button(onClick = { showChangePasswordDialog = false }) { Text("Close") }
                } else {
                    Button(
                        onClick = {
                            pwError = null
                            if (currentPw.isBlank()) { pwError = "Enter your current password"; return@Button }
                            if (newPw.length < 8) { pwError = "New password must be at least 8 characters"; return@Button }
                            if (!newPw.any { it.isUpperCase() }) { pwError = "New password needs an uppercase letter"; return@Button }
                            if (!newPw.any { it.isLowerCase() }) { pwError = "New password needs a lowercase letter"; return@Button }
                            if (!newPw.any { it.isDigit() }) { pwError = "New password needs a digit"; return@Button }
                            if (!newPw.any { it in "!@#\$%^&*(),.?\":{}|<>" }) { pwError = "New password needs a special character"; return@Button }
                            if (newPw != confirmPw) { pwError = "Passwords do not match"; return@Button }
                            pwLoading = true
                            scope.launch {
                                try {
                                    NetworkModule.apiService.updatePassword(PasswordUpdate(currentPw, newPw))
                                    pwSuccess = true
                                } catch (e: HttpException) {
                                    val body = e.response()?.errorBody()?.string()
                                    pwError = try {
                                        val json = org.json.JSONObject(body ?: "")
                                        val d = json.get("detail")
                                        if (d is String) d else json.getJSONArray("detail").getJSONObject(0).getString("msg")
                                    } catch (_: Exception) { "Failed (${e.code()})" }
                                } catch (e: Exception) {
                                    pwError = e.message ?: "Failed to change password"
                                } finally {
                                    pwLoading = false
                                }
                            }
                        },
                        enabled = !pwLoading
                    ) {
                        if (pwLoading) CircularProgressIndicator(modifier = Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                        else Text("Change")
                    }
                }
            },
            dismissButton = {
                if (!pwSuccess) {
                    TextButton(onClick = { showChangePasswordDialog = false }, enabled = !pwLoading) {
                        Text(stringResource(R.string.cancel))
                    }
                }
            }
        )
    }
}

// ── Reusable Settings Components ─────────────────────────────────────────────

@Composable
fun SettingsSectionHeader(title: String) {
    Text(
        text = title,
        fontSize = 13.sp,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(start = 16.dp, bottom = 6.dp)
    )
}

@Composable
fun SettingsGroup(content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column { content() }
    }
}

@Composable
fun SettingsItem(
    icon: ImageVector,
    iconBg: Color,
    title: String,
    subtitle: String? = null,
    subtitleColor: Color = Color.Unspecified,
    onClick: () -> Unit = {}
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(iconBg.copy(alpha = 0.12f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = iconBg, modifier = Modifier.size(20.dp))
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(title, fontSize = 15.sp, fontWeight = FontWeight.Medium)
            if (subtitle != null) {
                Text(subtitle, fontSize = 13.sp, color = if (subtitleColor == Color.Unspecified) MaterialTheme.colorScheme.onSurfaceVariant else subtitleColor)
            }
        }
        Icon(Icons.Default.KeyboardArrowRight, contentDescription = null, tint = Color.LightGray)
    }
}

@Composable
fun SettingsToggle(
    icon: ImageVector,
    iconBg: Color,
    title: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(iconBg.copy(alpha = 0.12f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = iconBg, modifier = Modifier.size(20.dp))
        }
        Spacer(modifier = Modifier.width(12.dp))
        Text(title, fontSize = 15.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = Color(0xFF333333)
            )
        )
    }
}

@Composable
fun SettingsDivider() {
    Divider(
        modifier = Modifier.padding(start = 64.dp),
        color = MaterialTheme.colorScheme.outlineVariant,
        thickness = 1.dp
    )
}
