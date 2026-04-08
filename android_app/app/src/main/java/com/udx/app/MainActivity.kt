package com.udx.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp
import androidx.compose.ui.Alignment
import android.content.Context
import com.udx.app.data.NetworkModule
import com.udx.app.data.TokenManager
import com.udx.app.ui.screens.*
import com.udx.app.ui.theme.LocalThemeState
import com.udx.app.ui.theme.ThemeState
import com.udx.app.ui.theme.UDXTheme
import com.udx.app.utils.LocaleHelper
import com.udx.app.utils.ThemePreference
import com.udx.app.ui.viewmodels.CartViewModel
import androidx.compose.runtime.CompositionLocalProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(LocaleHelper.onAttach(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        TokenManager.init(this)

        setContent {
            var isDark by remember { mutableStateOf(ThemePreference.isDarkMode(this)) }

            val themeState = ThemeState(
                isDark = isDark,
                toggle = {
                    isDark = !isDark
                    ThemePreference.setDarkMode(this, isDark)
                }
            )

            CompositionLocalProvider(LocalThemeState provides themeState) {
                UDXTheme(darkTheme = isDark) {
                    Surface(
                        modifier = Modifier.fillMaxSize(),
                        color = MaterialTheme.colorScheme.background
                    ) {
                        AppNavigation()
                    }
                }
            }
        }
    }
}

sealed class MainTab(val route: String, val title: String, val icon: ImageVector) {
    object Dashboard : MainTab("dashboard", "Marketplace", Icons.Default.Home)
    object Add : MainTab("add", "Add", Icons.Default.Add)
    object Contracts : MainTab("contracts", "Contracts", Icons.Default.Menu)
    object Trends : MainTab("trends", "Market Trends", Icons.Default.Star)
    object Profile : MainTab("profile", "Settings", Icons.Default.Settings)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppScaffold(
    onLogout: () -> Unit,
    onNavigateToChat: () -> Unit,
    onNavigateToCart: () -> Unit,
    onNavigateToCategory: (String, String) -> Unit,
    onNavigateToSeller: (String) -> Unit = {},
    cartViewModel: CartViewModel,
    initialRole: String = "buyer"
) {
    val cartItemCount by cartViewModel.cartItems.collectAsState()
    val count = cartItemCount.sumOf { it.quantity }

    val scope = rememberCoroutineScope()
    var selectedTab by remember { mutableStateOf<MainTab>(MainTab.Dashboard) }
    var showAddProduct by remember { mutableStateOf(false) }
    // buyer yoki seller modeda ishlash — initialRole dan boshlanadi
    var currentMode by remember { mutableStateOf(initialRole) }
    val isSeller = currentMode == "seller"

    val baseTabs = listOf(MainTab.Dashboard, MainTab.Contracts, MainTab.Trends, MainTab.Profile)
    val tabs = if (isSeller) listOf(MainTab.Dashboard, MainTab.Add, MainTab.Contracts, MainTab.Trends, MainTab.Profile) else baseTabs

    if (showAddProduct) {
        AddProductScreen(
            onBack = { showAddProduct = false },
            onSuccess = { showAddProduct = false }
        )
    } else {
        Scaffold(
            bottomBar = {
                NavigationBar(
                    containerColor = MaterialTheme.colorScheme.surface,
                    contentColor = MaterialTheme.colorScheme.onSurface
                ) {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            icon = { Icon(tab.icon, contentDescription = tab.title) },
                            label = {
                                Text(tab.title, fontSize = 10.sp, maxLines = 1, softWrap = false)
                            },
                            selected = selectedTab == tab,
                            onClick = {
                                if (tab == MainTab.Add) showAddProduct = true
                                else selectedTab = tab
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = Color(0xFF9C27B0),
                                selectedTextColor = Color(0xFF9C27B0),
                                indicatorColor = Color.Transparent
                            )
                        )
                    }
                }
            }
        ) { paddingValues ->
            Box(modifier = Modifier.padding(paddingValues)) {
                when (selectedTab) {
                    MainTab.Dashboard -> DashboardScreen(
                        onLogout = onLogout,
                        onAddProduct = { if (isSeller) showAddProduct = true },
                        onNavigateToMessages = onNavigateToChat,
                        onNavigateToCart = onNavigateToCart,
                        onNavigateToSettings = { selectedTab = MainTab.Profile },
                        onNavigateToCategory = onNavigateToCategory,
                        onAddToCart = { cartViewModel.addToCart(it) },
                        onNavigateToSeller = onNavigateToSeller,
                        cartItemCount = count,
                        isSeller = isSeller,
                        onSwitchRole = {
                            val newRole = if (isSeller) "buyer" else "seller"
                            currentMode = newRole
                            selectedTab = MainTab.Dashboard
                            scope.launch {
                                try {
                                    NetworkModule.apiService.updateRole(com.udx.app.data.RoleUpdate(newRole))
                                } catch (_: Exception) {}
                            }
                        }
                    )
                    MainTab.Add -> { /* onClick da handle qilinadi */ }
                    MainTab.Contracts -> ContractsScreen(onBack = { selectedTab = MainTab.Dashboard })
                    MainTab.Trends -> MarketTrendsScreen(onBack = { selectedTab = MainTab.Dashboard })
                    MainTab.Profile -> ProfileScreen(onLogout = onLogout)
                }
            }
        }
    }
}

@Composable
fun AppNavigation() {
    var currentScreen by remember { mutableStateOf("checking") }
    var googleAuthUrl by remember { mutableStateOf("") }
    var selectedCategoryId by remember { mutableStateOf("") }
    var selectedCategoryName by remember { mutableStateOf("") }
    var selectedSellerId by remember { mutableStateOf("") }
    var userRole by remember { mutableStateOf("buyer") }
    val cartViewModel: CartViewModel = viewModel()

    // Validate token on first launch
    LaunchedEffect(Unit) {
        if (TokenManager.getToken() != null) {
            try {
                val me = NetworkModule.apiService.getMe()
                userRole = me.role
                currentScreen = "main"
            } catch (e: Exception) {
                TokenManager.clearToken()
                currentScreen = "welcome"
            }
        } else {
            currentScreen = "welcome"
        }
    }

    when (currentScreen) {
        "checking" -> Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator()
        }
        "welcome" -> WelcomeScreen(
            onNavigateToLogin = { currentScreen = "login" },
            onNavigateToRegister = { currentScreen = "register" },
            onContinueAsGuest = { currentScreen = "main" }
        )
        "login" -> {
            androidx.activity.compose.BackHandler { currentScreen = "welcome" }
            LoginScreen(
                onLoginSuccess = { currentScreen = "main" },
                onNavigateToRegister = { currentScreen = "register" },
                onGoogleLogin = { authUrl ->
                    googleAuthUrl = authUrl
                    currentScreen = "google_auth"
                },
                onContinueAsGuest = { currentScreen = "main" }
            )
        }
        "register" -> {
            androidx.activity.compose.BackHandler { currentScreen = "welcome" }
            RegisterScreen(
                onRegisterSuccess = { currentScreen = "login" },
                onNavigateToLogin = { currentScreen = "login" },
                onGoogleRegister = { authUrl ->
                    googleAuthUrl = authUrl
                    currentScreen = "google_auth"
                }
            )
        }
        "google_auth" -> GoogleAuthWebViewScreen(
            authUrl = googleAuthUrl,
            onSuccess = { currentScreen = "main" },
            onCancel = { currentScreen = "welcome" }
        )
        "main" -> MainAppScaffold(
            onLogout = { currentScreen = "welcome" },
            onNavigateToChat = { currentScreen = "chat" },
            onNavigateToCart = { currentScreen = "cart" },
            onNavigateToCategory = { id, name ->
                selectedCategoryId = id
                selectedCategoryName = name
                currentScreen = "category"
            },
            onNavigateToSeller = { id ->
                selectedSellerId = id
                currentScreen = "seller_profile"
            },
            cartViewModel = cartViewModel,
            initialRole = userRole
        )
        "category" -> CategoryProductsScreen(
            categoryId = selectedCategoryId,
            categoryName = selectedCategoryName,
            onBack = { currentScreen = "main" },
            onAddToCart = { cartViewModel.addToCart(it) }
        )
        "seller_profile" -> SellerProfileScreen(
            sellerId = selectedSellerId,
            onBack = { currentScreen = "main" }
        )
        "chat" -> ChatScreen(onBack = { currentScreen = "main" })
        "cart" -> CartScreen(
            viewModel = cartViewModel,
            onBack = { currentScreen = "main" }
        )
    }
}
