import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card } from '../ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Search, Heart, Star, MapPin, ShoppingCart, Award, TrendingUp, Cloud, Mail, Globe, Settings, Store } from 'lucide-react';
import { products as initialProducts, farmers, categories, mockWeather, mockChats, type Product } from '../../data/mockData';
import { useTranslation } from '../../context/TranslationContext';
import { api } from '../../api';

interface BuyerHomeScreenProps {
  onProductClick: (productId: string) => void;
  onFarmerClick: (farmerId: string) => void;
  onCartClick: () => void;
  onMarketTrendsClick: () => void;
  onSettingsClick: () => void;
  onLanguageClick: () => void;
  onFavoritesClick: () => void;
  onMessagesClick: () => void;
  onSearchClick?: () => void;
  onSwitchToSeller?: () => void;
  cartItemCount: number;
  products?: Product[];
}

export function BuyerHomeScreen({
  onProductClick,
  onFarmerClick,
  onCartClick,
  onMarketTrendsClick,
  onSettingsClick,
  onLanguageClick,
  onFavoritesClick,
  onMessagesClick,
  onSearchClick,
  onSwitchToSeller,
  cartItemCount,
  products = initialProducts
}: BuyerHomeScreenProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('featured');
  const [selectedFarmers, setSelectedFarmers] = useState<Set<string>>(new Set());
  const [weather, setWeather] = useState<any>(mockWeather);
  const [isLoadingWeather, setIsLoadingWeather] = useState(false);

  // Fetch real weather data
  useEffect(() => {
    const fetchWeather = async () => {
      setIsLoadingWeather(true);
      try {
        // Get user's location
        if ('geolocation' in navigator) {
          navigator.geolocation.getCurrentPosition(
            async (position) => {
              try {
                const weatherData = await api.getWeather(
                  position.coords.latitude,
                  position.coords.longitude
                );
                setWeather({
                  temperature: weatherData.temperature,
                  condition: weatherData.condition,
                  icon: getWeatherIcon(weatherData.condition),
                  location: weatherData.location
                });
              } catch (error) {
                console.error('Failed to fetch weather:', error);
              } finally {
                setIsLoadingWeather(false);
              }
            },
            (error) => {
              console.error('Geolocation error:', error);
              setIsLoadingWeather(false);
            }
          );
        }
      } catch (error) {
        console.error('Weather fetch error:', error);
        setIsLoadingWeather(false);
      }
    };
    fetchWeather();
  }, []);

  const getWeatherIcon = (condition: string) => {
    const icons: Record<string, string> = {
      'Clear': '☀️',
      'Clouds': '☁️',
      'Rain': '🌧️',
      'Snow': '❄️',
      'Thunderstorm': '⛈️',
      'Drizzle': '🌦️',
      'Mist': '🌫️',
      'Fog': '🌫️'
    };
    return icons[condition] || '🌤️';
  };

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || product.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const totalUnreadMessages = mockChats.reduce((sum, chat) => sum + chat.unreadCount, 0);

  const onlineFarmers = farmers.filter(f => f.isOnline);

  const handleSelectFarmer = (farmerId: string) => {
    if (!selectedFarmers.has(farmerId)) {
      setSelectedFarmers(new Set([...selectedFarmers, farmerId]));
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-gradient-to-r from-[#af47ff] to-[#8b2dd1] px-4 py-4 text-white shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-white">UDX</h2>
            <p className="text-white/80">{t('buyer.home.subtitle')}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onMessagesClick} className="relative rounded-full p-1 hover:bg-background/10">
              <Mail className="h-6 w-6" />
              {totalUnreadMessages > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">
                  {totalUnreadMessages}
                </span>
              )}
            </button>
            <button onClick={onCartClick} className="relative rounded-full p-1 hover:bg-background/10">
              <ShoppingCart className="h-6 w-6" />
              {cartItemCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">
                  {cartItemCount}
                </span>
              )}
            </button>
            {onSwitchToSeller && (
              <Button
                onClick={onSwitchToSeller}
                variant="ghost"
                size="sm"
                className="bg-background/20 text-white hover:bg-background/30 h-8 px-2 text-xs"
              >
                <Store className="mr-1 h-4 w-4" />
                {t('role.seller')}
              </Button>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative" onClick={onSearchClick}>
          <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t('common.search') + ' (@nickname, name, phone)'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="border-none bg-background pl-10 pr-4 cursor-pointer"
            readOnly
          />
        </div>
      </div>

      <div className="px-4 py-4">
        {/* Weather & Market Trends */}
        <div className="mb-6 grid grid-cols-2 gap-3">
          <Card className="overflow-hidden bg-gradient-to-br from-blue-500 to-blue-600 p-4 text-white">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-white/80">{weather.location || t('buyer.home.weather')}</span>
              <span className="text-white">{weather.icon}</span>
            </div>
            <div className="mb-1">{weather.temperature}°C</div>
            <p className="text-white/90">{weather.condition}</p>
            {isLoadingWeather && <p className="text-white/60 text-xs mt-1">Loading...</p>}
          </Card>

          <Card
            className="overflow-hidden bg-gradient-to-br from-green-500 to-green-600 p-4 text-white"
            onClick={onMarketTrendsClick}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-white/80">{t('buyer.home.title')}</span>
              <TrendingUp className="h-5 w-5" />
            </div>
            <div className="mb-1">{t('trends.title')}</div>
            <p className="text-white/90">{t('seller.analytics')}</p>
          </Card>
        </div>

        {/* Categories */}
        <div className="mb-6">
          <h3 className="mb-3">{t('manageProducts.category')}</h3>
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`flex flex-shrink-0 flex-col items-center gap-2 rounded-xl p-4 transition-all ${selectedCategory === category.id
                    ? 'bg-[#af47ff] text-white'
                    : 'bg-background text-foreground'
                  }`}
                style={{ minWidth: '100px' }}
              >
                <span className="text-2xl">{category.icon}</span>
                <span className="whitespace-nowrap text-center">{t(category.name)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Online Farmers */}
        {onlineFarmers.length > 0 && (
          <div className="mb-6">
            <h3 className="mb-3">🟢 {t('buyer.home.onlineFarmers')}</h3>
            <div className="space-y-3">
              {onlineFarmers.map((farmer) => {
                const isSelected = selectedFarmers.has(farmer.id);
                const farmerProducts = products.filter(p => p.farmerId === farmer.id);

                return (
                  <Card key={farmer.id} className="overflow-hidden">
                    <div className="p-4">
                      <div className="mb-3 flex items-center gap-3">
                        <div className="relative">
                          <img
                            src={farmer.logo}
                            alt={farmer.name}
                            className="h-16 w-16 rounded-full object-cover"
                          />
                          <div className="absolute bottom-0 right-0 h-4 w-4 rounded-full border-2 border-background bg-green-500"></div>
                        </div>
                        <div className="flex-1">
                          <h4>{farmer.name}</h4>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                            <span>{farmer.rating}</span>
                            <span>•</span>
                            <span>{farmer.distance} {t('buyer.home.kmAway')}</span>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => handleSelectFarmer(farmer.id)}
                          disabled={isSelected}
                          className={isSelected ? 'bg-muted text-foreground' : 'bg-[#af47ff] hover:bg-[#9935e6]'}
                        >
                          {isSelected ? t('common.selected') : t('common.select')}
                        </Button>
                      </div>

                      {/* Farmer's Products */}
                      {farmerProducts.length > 0 && (
                        <div className="flex gap-2 overflow-x-auto pb-2">
                          {farmerProducts.map((product) => (
                            <div
                              key={product.id}
                              onClick={() => onProductClick(product.id)}
                              className="flex-shrink-0 cursor-pointer"
                              style={{ width: '120px' }}
                            >
                              <div className="mb-2 aspect-square overflow-hidden rounded-lg">
                                <img
                                  src={product.image}
                                  alt={product.name}
                                  className="h-full w-full object-cover"
                                />
                              </div>
                              <p className="line-clamp-1 text-sm">{product.name}</p>
                              <p className="text-sm text-[#af47ff]">${product.price}/{product.unit}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* Products */}
        <div className="mb-4 flex items-center justify-between">
          <h3>{t('buyer.home.allProducts')}</h3>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {filteredProducts.map((product) => (
            <motion.div
              key={product.id}
              whileTap={{ scale: 0.95 }}
              onClick={() => onProductClick(product.id)}
            >
              <Card className="overflow-hidden">
                <div className="relative aspect-square">
                  <img
                    src={product.image}
                    alt={product.name}
                    className="h-full w-full object-cover"
                  />
                  {product.certified && (
                    <Badge className="absolute right-2 top-2 bg-green-500">
                      <Award className="mr-1 h-3 w-3" />
                    </Badge>
                  )}
                </div>
                <div className="p-3">
                  <h4 className="mb-1 line-clamp-1">{product.name}</h4>
                  <div className="mb-2 flex items-center gap-2 text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                      <span>{product.rating}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      <span>{product.distance} km</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-[#af47ff]">
                        ${product.price}
                      </span>
                      <span className="text-muted-foreground">/{product.unit}</span>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
