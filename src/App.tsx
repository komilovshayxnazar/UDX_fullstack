import { useState, useEffect } from 'react';
import { WelcomeScreen } from './components/WelcomeScreen';
import { RoleSelectionScreen } from './components/RoleSelectionScreen';
import { RoleSwitcherScreen } from './components/RoleSwitcherScreen';
import { AuthScreen } from './components/AuthScreen';
import { UnifiedProfileScreen } from './components/UnifiedProfileScreen';
import { CompletionScreen } from './components/CompletionScreen';
import { LanguageSelectionScreen } from './components/LanguageSelectionScreen';
import { SettingsScreen } from './components/SettingsScreen';
import { BuyerHomeScreen } from './components/buyer/BuyerHomeScreen';
import { BottomNavigation } from './components/BottomNavigation';
import { LiveScreen } from './components/LiveScreen';
import { AddAdScreen } from './components/AddAdScreen';
import { ProductCardScreen } from './components/buyer/ProductCardScreen';
import { FarmerProfileScreen } from './components/buyer/FarmerProfileScreen';
import { CartScreen } from './components/buyer/CartScreen';
import { MarketTrendsScreen } from './components/buyer/MarketTrendsScreen';
import { CommunicationTypeScreen } from './components/communication/CommunicationTypeScreen';
import { VideoChatScreen } from './components/communication/VideoChatScreen';
import { FavoritesScreen } from './components/FavoritesScreen';
import { MessagesScreen } from './components/MessagesScreen';
import { ChatDetailScreen } from './components/ChatDetailScreen';
import { ContractsScreen } from './components/ContractsScreen';
import { AddContractOptionsScreen } from './components/AddContractOptionsScreen';
import { CreateContractScreen } from './components/CreateContractScreen';
import { MultiDeviceContractScreen } from './components/MultiDeviceContractScreen';
import { SearchScreen } from './components/SearchScreen';
import { SellerDashboard } from './components/seller/SellerDashboard';
import { ManageProductsScreen } from './components/seller/ManageProductsScreen';
import { MyProductsScreen } from './components/seller/MyProductsScreen';
import { OrdersScreen } from './components/seller/OrdersScreen';
import { TranslationProvider, useTranslation } from './context/TranslationContext';
import { Toaster, toast } from 'sonner';
import type { CartItem, Order, Product } from './data/mockData';
import { products as initialProducts, languages } from './data/mockData';
import { api } from './api';

type OnboardingScreen = 'welcome' | 'auth' | 'profile' | 'complete' | 'language' | 'settings';
type BuyerScreen = 'home' | 'product' | 'farmer' | 'cart' | 'trends' | 'communication' | 'video' | 'settings' | 'language' | 'favorites' | 'messages' | 'chat-detail' | 'live' | 'add' | 'contracts' | 'add-contract-options' | 'create-contract' | 'multi-device-contract' | 'search';
type SellerScreen = 'dashboard' | 'products' | 'my-products' | 'orders' | 'settings' | 'language' | 'messages' | 'chat-detail' | 'favorites' | 'live' | 'add' | 'trends' | 'contracts' | 'add-contract-options' | 'create-contract' | 'multi-device-contract' | 'search';
type ActiveMode = 'buyer' | 'seller' | null;
type BottomTab = 'home' | 'live' | 'add' | 'contracts' | 'trends' | 'profile';

function AppContent() {
  const { setLanguage } = useTranslation();
  const [currentOnboardingScreen, setCurrentOnboardingScreen] = useState<OnboardingScreen>('welcome');
  const [currentBuyerScreen, setCurrentBuyerScreen] = useState<BuyerScreen>('home');
  const [currentSellerScreen, setCurrentSellerScreen] = useState<SellerScreen>('dashboard');
  const [activeMode, setActiveMode] = useState<ActiveMode>(null);
  const [isOnboarded, setIsOnboarded] = useState(false);
  const [showRoleSwitcher, setShowRoleSwitcher] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [selectedFarmerId, setSelectedFarmerId] = useState<string | null>(null);
  const [selectedFarmerName, setSelectedFarmerName] = useState<string>('');
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [buyerBottomTab, setBuyerBottomTab] = useState<BottomTab>('home');
  const [sellerBottomTab, setSellerBottomTab] = useState<BottomTab>('home');
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [currentUser, setCurrentUser] = useState<any>(null);

  // Fetch products from backend
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const data = await api.getProducts();
        if (data && data.length > 0) {
          setProducts(data);
        }
      } catch (error) {
        console.error('Failed to fetch products from backend, using mock data:', error);
      }
    };
    fetchProducts();
  }, []);

  // Handle Google OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');

    if (tokenFromUrl && window.location.pathname === '/auth/callback') {
      // Save token
      setToken(tokenFromUrl);
      localStorage.setItem('token', tokenFromUrl);

      // Clear URL params
      window.history.replaceState({}, document.title, '/');

      // Complete onboarding
      setIsOnboarded(true);
      setActiveMode('buyer'); // Default to buyer for Google OAuth users
      toast.success('Successfully signed in with Google!');
    }
  }, []);

  // Fetch current user data when token is available
  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        try {
          const userData = await api.getCurrentUser(token);
          setCurrentUser(userData);
        } catch (error) {
          console.error('Failed to fetch user data:', error);
        }
      }
    };
    fetchUser();
  }, [token]);

  const [cart, setCart] = useState<CartItem[]>([]);
  const [orderHistory, setOrderHistory] = useState<Order[]>([
    {
      id: '001',
      date: '2025-10-15',
      status: 'completed',
      total: 45.99,
      deliveryMethod: 'courier',
      items: [
        { productId: '1', quantity: 2 },
        { productId: '2', quantity: 3 },
      ],
    },
    {
      id: '002',
      date: '2025-10-10',
      status: 'in-process',
      total: 28.50,
      deliveryMethod: 'pickup',
      items: [
        { productId: '3', quantity: 1 },
      ],
    },
  ]);
  const [favoriteProductIds, setFavoriteProductIds] = useState<string[]>(['1', '3']); // Mock favorites
  const [currentLanguage, setCurrentLanguage] = useState('en');
  const [products, setProducts] = useState<Product[]>(initialProducts);
  const [previousOnboardingScreen, setPreviousOnboardingScreen] = useState<OnboardingScreen | null>(null);
  const [previousBuyerScreen, setPreviousBuyerScreen] = useState<BuyerScreen | null>(null);
  const [previousSellerScreen, setPreviousSellerScreen] = useState<SellerScreen | null>(null);

  // Onboarding
  const handleContinueFromWelcome = () => setCurrentOnboardingScreen('auth');
  const handleAuthComplete = (isGuest?: boolean, accessToken?: string) => {
    if (accessToken) {
      setToken(accessToken);
      localStorage.setItem('token', accessToken);
    }

    if (isGuest) {
      setCurrentOnboardingScreen('complete');
      setTimeout(() => {
        setIsOnboarded(true);
        setShowRoleSwitcher(true);
      }, 3000);
    } else {
      setCurrentOnboardingScreen('profile');
    }
  };
  const handleProfileComplete = () => {
    setCurrentOnboardingScreen('complete');
    setTimeout(() => {
      setIsOnboarded(true);
      setShowRoleSwitcher(true);
    }, 3000);
  };
  const handleOnboardingBack = () => {
    switch (currentOnboardingScreen) {
      case 'auth': setCurrentOnboardingScreen('welcome'); break;
      case 'profile': setCurrentOnboardingScreen('auth'); break;
    }
  };

  // Mode switching
  const handleSelectMode = (mode: 'buyer' | 'seller') => {
    setActiveMode(mode);
    setShowRoleSwitcher(false);
  };

  // Buyer navigation
  const handleProductClick = (productId: string) => {
    setSelectedProductId(productId);
    setCurrentBuyerScreen('product');
  };
  const handleFarmerClick = (farmerId: string) => {
    setSelectedFarmerId(farmerId);
    setCurrentBuyerScreen('farmer');
  };
  const handleCartClick = () => setCurrentBuyerScreen('cart');
  const handleMarketTrendsClick = () => setCurrentBuyerScreen('trends');
  const handleChatClick = (farmerId: string, farmerName: string) => {
    setSelectedFarmerId(farmerId);
    setSelectedFarmerName(farmerName);
    setCurrentBuyerScreen('communication');
  };
  const handleVideoChatStart = () => setCurrentBuyerScreen('video');
  const handleSettingsClick = () => setCurrentBuyerScreen('settings');
  const handleLanguageClick = () => {
    setPreviousBuyerScreen(currentBuyerScreen);
    setCurrentBuyerScreen('language');
  };
  const handleFavoritesClick = () => setCurrentBuyerScreen('favorites');
  const handleMessagesClick = () => setCurrentBuyerScreen('messages');
  const handleSearchClick = () => setCurrentBuyerScreen('search');
  const handleBuyerBack = () => {
    setCurrentBuyerScreen('home');
    setSelectedProductId(null);
    setSelectedFarmerId(null);
  };

  // Favorites
  const handleRemoveFavorite = (productId: string) => {
    setFavoriteProductIds(prev => prev.filter(id => id !== productId));
  };

  // Language
  const handleLanguageSelect = (languageCode: string) => {
    setCurrentLanguage(languageCode);
    setLanguage(languageCode as any);

    // Find the selected language name
    const selectedLang = languages.find(l => l.code === languageCode);
    if (selectedLang) {
      toast.success(`Language changed to ${selectedLang.name} ${selectedLang.flag}`);
    }

    // Return to previous screen instead of settings
    if (previousOnboardingScreen) {
      setCurrentOnboardingScreen(previousOnboardingScreen);
      setPreviousOnboardingScreen(null);
    } else if (previousBuyerScreen) {
      setCurrentBuyerScreen(previousBuyerScreen);
      setPreviousBuyerScreen(null);
    } else if (previousSellerScreen) {
      setCurrentSellerScreen(previousSellerScreen);
      setPreviousSellerScreen(null);
    }
  };

  const handleOnboardingLanguageClick = () => {
    setPreviousOnboardingScreen(currentOnboardingScreen);
    setCurrentOnboardingScreen('language');
  };

  const handleOnboardingSettingsClick = () => {
    setPreviousOnboardingScreen(currentOnboardingScreen);
    setCurrentOnboardingScreen('settings');
  };

  // Bottom navigation handlers
  const handleBuyerBottomTabChange = (tab: BottomTab) => {
    setBuyerBottomTab(tab);
    switch (tab) {
      case 'home':
        setCurrentBuyerScreen('home');
        break;
      case 'live':
        setCurrentBuyerScreen('live');
        break;
      case 'add':
        setCurrentBuyerScreen('add');
        break;
      case 'contracts':
        setCurrentBuyerScreen('contracts');
        break;
      case 'trends':
        setCurrentBuyerScreen('trends');
        break;
      case 'profile':
        setCurrentBuyerScreen('settings');
        break;
    }
  };

  const handleSellerBottomTabChange = (tab: BottomTab) => {
    setSellerBottomTab(tab);
    switch (tab) {
      case 'home':
        setCurrentSellerScreen('dashboard');
        break;
      case 'live':
        setCurrentSellerScreen('live');
        break;
      case 'add':
        setCurrentSellerScreen('add');
        break;
      case 'contracts':
        setCurrentSellerScreen('contracts');
        break;
      case 'trends':
        setCurrentSellerScreen('trends');
        break;
      case 'profile':
        setCurrentSellerScreen('settings');
        break;
    }
  };

  // Add product handler
  const handleProductAdded = (product: Product) => {
    setProducts([...products, product]);
  };

  // Logout
  const handleLogout = () => {
    setIsOnboarded(false);
    setActiveMode(null);
    setToken(null);
    localStorage.removeItem('token');
    setCurrentOnboardingScreen('welcome');
    setCurrentBuyerScreen('home');
  };

  // Cart
  const handleAddToCart = (productId: string, quantity: number) => {
    setCart(prevCart => {
      const existing = prevCart.find(item => item.productId === productId);
      if (existing) {
        return prevCart.map(item =>
          item.productId === productId ? { ...item, quantity: item.quantity + quantity } : item
        );
      }
      return [...prevCart, { productId, quantity }];
    });
  };
  const handleUpdateCartQuantity = (productId: string, quantity: number) => {
    setCart(prevCart => prevCart.map(item =>
      item.productId === productId ? { ...item, quantity } : item
    ));
  };
  const handleRemoveFromCart = (productId: string) => {
    setCart(prevCart => prevCart.filter(item => item.productId !== productId));
  };

  const cartItemCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  // Onboarding flow
  if (!isOnboarded) {
    return (
      <div className="mx-auto max-w-md">
        {currentOnboardingScreen === 'welcome' && (
          <WelcomeScreen
            onContinue={handleContinueFromWelcome}
            onLanguageClick={handleOnboardingLanguageClick}
            onSettingsClick={handleOnboardingSettingsClick}
          />
        )}
        {currentOnboardingScreen === 'auth' && (
          <AuthScreen
            role="buyer"
            onComplete={handleAuthComplete}
            onBack={handleOnboardingBack}
          />
        )}
        {currentOnboardingScreen === 'profile' && (
          <UnifiedProfileScreen
            onComplete={handleProfileComplete}
            onBack={handleOnboardingBack}
          />
        )}
        {currentOnboardingScreen === 'complete' && (
          <CompletionScreen role="buyer" />
        )}
        {currentOnboardingScreen === 'language' && (
          <LanguageSelectionScreen
            onBack={() => {
              if (previousOnboardingScreen) {
                setCurrentOnboardingScreen(previousOnboardingScreen);
                setPreviousOnboardingScreen(null);
              }
            }}
            currentLanguage={currentLanguage}
            onLanguageSelect={handleLanguageSelect}
          />
        )}
        {currentOnboardingScreen === 'settings' && (
          <SettingsScreen
            onBack={() => {
              if (previousOnboardingScreen) {
                setCurrentOnboardingScreen(previousOnboardingScreen);
                setPreviousOnboardingScreen(null);
              }
            }}
            onLanguageClick={handleOnboardingLanguageClick}
            onLogout={() => { }}
            onLogin={() => {
              setCurrentOnboardingScreen('auth');
            }}
            user={currentUser}
            onTopUp={async (amount) => {
              if (token) {
                const updatedUser = await api.depositBalance(amount, token);
                setCurrentUser(updatedUser);
                toast.success(`Successfully deposited $${amount.toFixed(2)}`);
              }
            }}
            onWithdraw={async (amount) => {
              if (token) {
                const updatedUser = await api.withdrawBalance(amount, token);
                setCurrentUser(updatedUser);
                toast.success(`Successfully withdrew $${amount.toFixed(2)}`);
              }
            }}
            token={token}
            onUserUpdated={setCurrentUser}
          />
        )}
      </div>
    );
  }

  // Role Switcher (shown after onboarding)
  if (showRoleSwitcher) {
    return (
      <div className="mx-auto max-w-md">
        <Toaster />
        <RoleSwitcherScreen onSelectMode={handleSelectMode} />
      </div>
    );
  }

  // Buyer module
  if (activeMode === 'buyer') {
    return (
      <div className="mx-auto max-w-md relative">
        <Toaster />
        {currentBuyerScreen === 'home' && (
          <>
            <BuyerHomeScreen
              onProductClick={handleProductClick}
              onFarmerClick={handleFarmerClick}
              onCartClick={handleCartClick}
              onMarketTrendsClick={handleMarketTrendsClick}
              onSettingsClick={handleSettingsClick}
              onLanguageClick={handleLanguageClick}
              onFavoritesClick={handleFavoritesClick}
              onMessagesClick={handleMessagesClick}
              onSearchClick={handleSearchClick}
              onSwitchToSeller={() => {
                setActiveMode('seller');
                setCurrentSellerScreen('dashboard');
              }}
              cartItemCount={cartItemCount}
              products={products}
            />
            <BottomNavigation activeTab={buyerBottomTab} onTabChange={handleBuyerBottomTabChange} mode="buyer"} />
          </>
        )}
        {currentBuyerScreen === 'live' && (
          <>
            <LiveScreen userRole="buyer" />
            <BottomNavigation activeTab={buyerBottomTab} onTabChange={handleBuyerBottomTabChange} mode="buyer"} />
          </>
        )}
        {currentBuyerScreen === 'add' && (
          <>
            <AddAdScreen onProductAdded={handleProductAdded} token={token} />
            <BottomNavigation activeTab={buyerBottomTab} onTabChange={handleBuyerBottomTabChange} mode="buyer"} />
          </>
        )}
        {currentBuyerScreen === 'product' && selectedProductId && (
          <ProductCardScreen
            productId={selectedProductId}
            onBack={handleBuyerBack}
            onFarmerClick={handleFarmerClick}
            onChatClick={(farmerId) => {
              const product = products.find((p: any) => p.id === selectedProductId);
              handleChatClick(farmerId, product?.farmerName || 'Farmer');
            }}
            onAddToCart={handleAddToCart}
            products={products}
          />
        )}
        {currentBuyerScreen === 'farmer' && selectedFarmerId && (
          <FarmerProfileScreen
            farmerId={selectedFarmerId}
            onBack={handleBuyerBack}
            onProductClick={handleProductClick}
          />
        )}
        {currentBuyerScreen === 'cart' && (
          <CartScreen
            onBack={handleBuyerBack}
            cart={cart}
            onUpdateQuantity={handleUpdateCartQuantity}
            onRemoveItem={handleRemoveFromCart}
            orderHistory={orderHistory}
          />
        )}
        {currentBuyerScreen === 'trends' && (
          <>
            <MarketTrendsScreen onBack={handleBuyerBack} />
            <BottomNavigation activeTab={buyerBottomTab} onTabChange={handleBuyerBottomTabChange} mode="buyer"} />
          </>
        )}
        {currentBuyerScreen === 'communication' && (
          <CommunicationTypeScreen
            farmerName={selectedFarmerName}
            onBack={handleBuyerBack}
            onSelectType={(type) => {
              if (type === 'video') handleVideoChatStart();
            }}
          />
        )}
        {currentBuyerScreen === 'video' && (
          <VideoChatScreen
            farmerName={selectedFarmerName}
            farmerId={selectedFarmerId ?? undefined}
            onEndCall={handleBuyerBack}
            onAddToFavorites={(_farmerId) => {
              // Add farmer/seller to favorites (mock implementation)
              toast.success(`${selectedFarmerName} added to favorites!`);
            }}
            isFavorite={false}
          />
        )}
        {currentBuyerScreen === 'settings' && (
          <SettingsScreen
            onBack={handleBuyerBack}
            onLanguageClick={handleLanguageClick}
            onLogout={handleLogout}
            onLogin={() => {
              setIsOnboarded(false);
              setCurrentOnboardingScreen('auth');
            }}
            user={currentUser}
            onTopUp={async (amount) => {
              if (token) {
                const updatedUser = await api.depositBalance(amount, token);
                setCurrentUser(updatedUser);
                toast.success(`Successfully deposited $${amount.toFixed(2)}`);
              }
            }}
            onWithdraw={async (amount) => {
              if (token) {
                const updatedUser = await api.withdrawBalance(amount, token);
                setCurrentUser(updatedUser);
                toast.success(`Successfully withdrew $${amount.toFixed(2)}`);
              }
            }}
            token={token}
            onUserUpdated={setCurrentUser}
          />
        )}
        {currentBuyerScreen === 'language' && (
          <LanguageSelectionScreen
            onBack={() => {
              if (previousBuyerScreen) {
                setCurrentBuyerScreen(previousBuyerScreen);
                setPreviousBuyerScreen(null);
              } else {
                setCurrentBuyerScreen('settings');
              }
            }}
            currentLanguage={currentLanguage}
            onLanguageSelect={handleLanguageSelect}
          />
        )}
        {currentBuyerScreen === 'favorites' && (
          <FavoritesScreen
            onBack={handleBuyerBack}
            onProductClick={handleProductClick}
            onChatClick={handleChatClick}
            favoriteProductIds={favoriteProductIds}
            onRemoveFavorite={handleRemoveFavorite}
          />
        )}
        {currentBuyerScreen === 'messages' && (
          <MessagesScreen
            onBack={handleBuyerBack}
            onChatClick={(chatId) => {
              setSelectedChatId(chatId);
              setCurrentBuyerScreen('chat-detail');
            }}
          />
        )}
        {currentBuyerScreen === 'chat-detail' && selectedChatId && (
          <ChatDetailScreen
            chatId={selectedChatId}
            onBack={() => {
              setSelectedChatId(null);
              setCurrentBuyerScreen('messages');
            }}
          />
        )}
        {currentBuyerScreen === 'contracts' && (
          <>
            <ContractsScreen
              onBack={handleBuyerBack}
              onAddContract={() => setCurrentBuyerScreen('add-contract-options')}
            />
            <BottomNavigation activeTab={buyerBottomTab} onTabChange={handleBuyerBottomTabChange} mode="buyer"} />
          </>
        )}
        {currentBuyerScreen === 'add-contract-options' && (
          <AddContractOptionsScreen
            onBack={() => setCurrentBuyerScreen('contracts')}
            onCreateNew={() => setCurrentBuyerScreen('create-contract')}
            onCreateMultiDevice={() => setCurrentBuyerScreen('multi-device-contract')}
            onSelectFromFiles={() => {
              // TODO: Implement file selection
              console.log('Select from files');
            }}
            onTakePicture={() => {
              // TODO: Implement camera
              console.log('Take picture');
            }}
          />
        )}
        {currentBuyerScreen === 'create-contract' && (
          <CreateContractScreen
            onBack={() => setCurrentBuyerScreen('add-contract-options')}
            onComplete={() => setCurrentBuyerScreen('contracts')}
          />
        )}
        {currentBuyerScreen === 'multi-device-contract' && (
          <MultiDeviceContractScreen
            onBack={() => setCurrentBuyerScreen('add-contract-options')}
            onComplete={() => setCurrentBuyerScreen('contracts')}
          />
        )}
        {currentBuyerScreen === 'search' && (
          <SearchScreen
            onBack={handleBuyerBack}
            onUserClick={(userId) => {
              // Navigate to user profile or chat
              console.log('View user profile:', userId);
            }}
            onSellerClick={(sellerId) => {
              handleFarmerClick(sellerId);
            }}
          />
        )}
      </div>
    );
  }

  // Seller navigation
  const handleSellerLanguageClick = () => {
    setPreviousSellerScreen(currentSellerScreen);
    setCurrentSellerScreen('language');
  };

  // Seller module
  if (activeMode === 'seller') {
    return (
      <div className="mx-auto max-w-md relative">
        <Toaster />
        {currentSellerScreen === 'dashboard' && (
          <>
            <SellerDashboard
              onManageProducts={() => setCurrentSellerScreen('products')}
              onManageOrders={() => setCurrentSellerScreen('orders')}
              onMyProducts={() => setCurrentSellerScreen('my-products')}
              onViewAnalytics={() => setCurrentSellerScreen('trends')}
              onSettingsClick={() => setCurrentSellerScreen('settings')}
              onLanguageClick={handleSellerLanguageClick}
              onFavoritesClick={() => setCurrentSellerScreen('favorites')}
              onMessagesClick={() => setCurrentSellerScreen('messages')}
              onSearchClick={() => setCurrentSellerScreen('search')}
              onSwitchToBuyer={() => {
                setActiveMode('buyer');
                setCurrentBuyerScreen('home');
              }}
            />
            <BottomNavigation activeTab={sellerBottomTab} onTabChange={handleSellerBottomTabChange} mode="seller"} />
          </>
        )}
        {currentSellerScreen === 'products' && (
          <ManageProductsScreen
            onBack={() => setCurrentSellerScreen('dashboard')}
            products={products}
            onProductAdded={handleProductAdded}
            token={token}
          />
        )}
        {currentSellerScreen === 'my-products' && (
          <MyProductsScreen
            onBack={() => setCurrentSellerScreen('dashboard')}
            products={products}
          />
        )}
        {currentSellerScreen === 'orders' && (
          <OrdersScreen onBack={() => setCurrentSellerScreen('dashboard')} />
        )}
        {currentSellerScreen === 'live' && (
          <>
            <LiveScreen userRole="seller" />
            <BottomNavigation activeTab={sellerBottomTab} onTabChange={handleSellerBottomTabChange} mode="seller"} />
          </>
        )}
        {currentSellerScreen === 'add' && (
          <>
            <AddAdScreen onProductAdded={handleProductAdded} token={token} />
            <BottomNavigation activeTab={sellerBottomTab} onTabChange={handleSellerBottomTabChange} mode="seller"} />
          </>
        )}
        {currentSellerScreen === 'trends' && (
          <>
            <MarketTrendsScreen onBack={() => setCurrentSellerScreen('dashboard')} />
            <BottomNavigation activeTab={sellerBottomTab} onTabChange={handleSellerBottomTabChange} mode="seller"} />
          </>
        )}
        {currentSellerScreen === 'settings' && (
          <SettingsScreen
            onBack={() => setCurrentSellerScreen('dashboard')}
            onLanguageClick={handleSellerLanguageClick}
            onLogout={handleLogout}
            onLogin={() => {
              setIsOnboarded(false);
              setCurrentOnboardingScreen('auth');
            }}
            user={currentUser}
            onTopUp={async (amount) => {
              if (token) {
                const updatedUser = await api.depositBalance(amount, token);
                setCurrentUser(updatedUser);
                toast.success(`Successfully deposited $${amount.toFixed(2)}`);
              }
            }}
            onWithdraw={async (amount) => {
              if (token) {
                const updatedUser = await api.withdrawBalance(amount, token);
                setCurrentUser(updatedUser);
                toast.success(`Successfully withdrew $${amount.toFixed(2)}`);
              }
            }}
            token={token}
            onUserUpdated={setCurrentUser}
          />
        )}
        {currentSellerScreen === 'language' && (
          <LanguageSelectionScreen
            onBack={() => {
              if (previousSellerScreen) {
                setCurrentSellerScreen(previousSellerScreen);
                setPreviousSellerScreen(null);
              } else {
                setCurrentSellerScreen('settings');
              }
            }}
            currentLanguage={currentLanguage}
            onLanguageSelect={handleLanguageSelect}
          />
        )}
        {currentSellerScreen === 'messages' && (
          <MessagesScreen
            onBack={() => setCurrentSellerScreen('dashboard')}
            onChatClick={(chatId) => {
              setSelectedChatId(chatId);
              setCurrentSellerScreen('chat-detail');
            }}
          />
        )}
        {currentSellerScreen === 'chat-detail' && selectedChatId && (
          <ChatDetailScreen
            chatId={selectedChatId}
            onBack={() => {
              setSelectedChatId(null);
              setCurrentSellerScreen('messages');
            }}
          />
        )}
        {currentSellerScreen === 'favorites' && (
          <FavoritesScreen
            onBack={() => setCurrentSellerScreen('dashboard')}
            onProductClick={() => { }}
            onChatClick={() => { }}
            favoriteProductIds={favoriteProductIds}
            onRemoveFavorite={handleRemoveFavorite}
          />
        )}
        {currentSellerScreen === 'contracts' && (
          <>
            <ContractsScreen
              onBack={() => setCurrentSellerScreen('dashboard')}
              onAddContract={() => setCurrentSellerScreen('add-contract-options')}
            />
            <BottomNavigation activeTab={sellerBottomTab} onTabChange={handleSellerBottomTabChange} mode="seller"} />
          </>
        )}
        {currentSellerScreen === 'add-contract-options' && (
          <AddContractOptionsScreen
            onBack={() => setCurrentSellerScreen('contracts')}
            onCreateNew={() => setCurrentSellerScreen('create-contract')}
            onCreateMultiDevice={() => setCurrentSellerScreen('multi-device-contract')}
            onSelectFromFiles={() => {
              // TODO: Implement file selection
              console.log('Select from files');
            }}
            onTakePicture={() => {
              // TODO: Implement camera
              console.log('Take picture');
            }}
          />
        )}
        {currentSellerScreen === 'create-contract' && (
          <CreateContractScreen
            onBack={() => setCurrentSellerScreen('add-contract-options')}
            onComplete={() => setCurrentSellerScreen('contracts')}
          />
        )}
        {currentSellerScreen === 'multi-device-contract' && (
          <MultiDeviceContractScreen
            onBack={() => setCurrentSellerScreen('add-contract-options')}
            onComplete={() => setCurrentSellerScreen('contracts')}
          />
        )}
        {currentSellerScreen === 'search' && (
          <SearchScreen
            onBack={() => setCurrentSellerScreen('dashboard')}
            onUserClick={(userId) => {
              // Navigate to user profile or chat
              console.log('View user profile:', userId);
            }}
            onSellerClick={(sellerId) => {
              // Navigate to seller profile
              console.log('View seller profile:', sellerId);
            }}
          />
        )}
      </div>
    );
  }

  return null;
}

export default function App() {
  return (
    <TranslationProvider>
      <AppContent />
    </TranslationProvider>
  );
}