export interface Product {
  id: string;
  name: string;
  price: number;
  unit: string;
  image: string;
  farmerId: string;
  farmerName: string;
  description: string;
  category: string;
  rating: number;
  reviewCount: number;
  distance: number;
  certified: boolean;
  inStock: boolean;
  gallery: string[];
  views?: number;
  sales?: number;
}

export interface Farmer {
  id: string;
  name: string;
  logo: string;
  rating: number;
  reviewCount: number;
  description: string;
  gallery: string[];
  phone: string;
  distance: number;
  tin: string;
  certifications: string[];
  products: string[];
  isOnline?: boolean;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
}

export const categories: Category[] = [
  { id: 'vegetables', name: 'vegetables', icon: '🥕' },
  { id: 'fruits', name: 'fruits', icon: '🍎' },
  { id: 'dairy', name: 'dairy', icon: '🥛' },
  { id: 'meat', name: 'meat', icon: '🥩' },
  { id: 'greens', name: 'greens', icon: '🥬' },
  { id: 'b2b', name: 'b2b', icon: '🏢' },
  { id: 'machinery', name: 'machinery', icon: '🚜' },
  { id: 'fertilizers', name: 'fertilizers', icon: '🧪' },
  { id: 'tools', name: 'tools', icon: '📦' },
  { id: 'grains', name: 'grains', icon: '🌾' },
  { id: 'finance', name: 'finance', icon: '💰' },
  { id: 'consulting', name: 'consulting', icon: '⚖️' },
  { id: 'organic', name: 'organic', icon: '🌿' },
  { id: 'seeds', name: 'seeds', icon: '🌱' },
  { id: 'storage', name: 'storage', icon: '🏗️' },
  { id: 'transport', name: 'transport', icon: '🚚' },
  { id: 'insurance', name: 'insurance', icon: '🛡️' },
  { id: 'livestock', name: 'livestock', icon: '🐄' },
];

export const products: Product[] = [
  {
    id: '1',
    name: 'Organic Tomatoes',
    price: 4.99,
    unit: 'kg',
    image: 'https://images.unsplash.com/photo-1546470427-227e99f9a46e?w=800',
    farmerId: 'f1',
    farmerName: 'Green Valley Farm',
    description: 'Fresh, organic tomatoes grown without pesticides. Perfect for salads, cooking, and canning.',
    category: 'vegetables',
    rating: 4.8,
    reviewCount: 45,
    distance: 2.5,
    certified: true,
    inStock: true,
    gallery: [
      'https://images.unsplash.com/photo-1546470427-227e99f9a46e?w=800',
      'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=800',
    ],
    views: 1234,
    sales: 89,
  },
  {
    id: '2',
    name: 'Fresh Lettuce',
    price: 2.99,
    unit: 'piece',
    image: 'https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=800',
    farmerId: 'f2',
    farmerName: 'Sunny Acres',
    description: 'Crisp, fresh lettuce harvested daily. Perfect for salads and sandwiches.',
    category: 'vegetables',
    rating: 4.6,
    reviewCount: 32,
    distance: 5.0,
    certified: true,
    inStock: true,
    gallery: ['https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=800'],
    views: 876,
    sales: 54,
  },
  {
    id: '3',
    name: 'Farm Fresh Milk',
    price: 5.99,
    unit: 'liter',
    image: 'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=800',
    farmerId: 'f3',
    farmerName: 'Happy Cow Dairy',
    description: 'Fresh pasteurized milk from grass-fed cows. Rich in nutrients.',
    category: 'dairy',
    rating: 4.7,
    reviewCount: 67,
    distance: 8.0,
    certified: false,
    inStock: true,
    gallery: ['https://images.unsplash.com/photo-1563636619-e9143da7973b?w=800'],
    views: 2100,
    sales: 143,
  },
];

export const farmers: Farmer[] = [
  {
    id: 'f1',
    name: 'Green Valley Farm',
    logo: 'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=400',
    rating: 4.8,
    reviewCount: 127,
    description: 'Family-owned organic farm specializing in vegetables and fruits.',
    gallery: [
      'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800',
      'https://images.unsplash.com/photo-1560493676-04071c5f467b?w=800',
    ],
    phone: '+1 (555) 123-4567',
    distance: 2.5,
    tin: '123456789',
    certifications: ['USDA Organic', 'Non-GMO'],
    products: ['1'],
    isOnline: true,
  },
  {
    id: 'f2',
    name: 'Sunny Acres',
    logo: 'https://images.unsplash.com/photo-1595855759920-86a3c7c65f5c?w=400',
    rating: 4.6,
    reviewCount: 89,
    description: 'Modern hydroponic farm producing fresh greens year-round.',
    gallery: ['https://images.unsplash.com/photo-1595855759920-86a3c7c65f5c?w=800'],
    phone: '+1 (555) 234-5678',
    distance: 5.0,
    tin: '987654321',
    certifications: ['Certified Naturally Grown'],
    products: ['2'],
    isOnline: false,
  },
  {
    id: 'f3',
    name: 'Happy Cow Dairy',
    logo: 'https://images.unsplash.com/photo-1516467508483-a7212febe31a?w=400',
    rating: 4.7,
    reviewCount: 156,
    description: 'Small-scale dairy farm with grass-fed cows.',
    gallery: ['https://images.unsplash.com/photo-1516467508483-a7212febe31a?w=800'],
    phone: '+1 (555) 345-6789',
    distance: 8.0,
    tin: '456789123',
    certifications: ['Grass-Fed Certified'],
    products: ['3'],
    isOnline: true,
  },
];

export interface CartItem {
  productId: string;
  quantity: number;
}

export interface Order {
  id: string;
  date: string;
  items: CartItem[];
  total: number;
  status: 'new' | 'in-process' | 'completed' | 'cancelled';
  deliveryMethod: 'courier' | 'pickup';
}

export interface Review {
  id: string;
  productId: string;
  userId: string;
  userName: string;
  rating: number;
  comment: string;
  date: string;
}

export interface MarketTrend {
  date: string;
  price: number;
}

export interface Weather {
  temperature: number;
  condition: string;
  humidity: number;
  windSpeed: number;
  icon: string;
}

export const mockWeather: Weather = {
  temperature: 24,
  condition: 'Partly Cloudy',
  humidity: 65,
  windSpeed: 12,
  icon: '⛅',
};

export const mockMarketTrends: MarketTrend[] = [
  { date: '2025-10-01', price: 4.50 },
  { date: '2025-10-02', price: 4.65 },
  { date: '2025-10-03', price: 4.55 },
  { date: '2025-10-04', price: 4.80 },
  { date: '2025-10-05', price: 4.99 },
  { date: '2025-10-06', price: 5.10 },
  { date: '2025-10-07', price: 5.05 },
];

export interface SellerStats {
  totalViews: number;
  totalSales: number;
  totalRevenue: number;
  activeProducts: number;
  newOrders: number;
}

export const mockSellerStats: SellerStats = {
  totalViews: 5430,
  totalSales: 342,
  totalRevenue: 15680.50,
  activeProducts: 12,
  newOrders: 8,
};

export interface FavoriteProduct {
  productId: string;
  addedDate: string;
}

export interface ChatMessage {
  id: string;
  senderId: string;
  text: string;
  timestamp: string;
}

export interface Chat {
  id: string;
  userId: string;
  userName: string;
  userAvatar: string;
  productId?: string;
  productName?: string;
  productImage?: string;
  lastMessage: string;
  lastMessageTime: string;
  unreadCount: number;
  orderStatus?: 'pending' | 'confirmed' | 'in-transit' | 'delivered' | 'completed';
  messages: ChatMessage[];
}

export interface Language {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
}

export const languages: Language[] = [
  // Original 15 languages
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇬🇧' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺' },
  { code: 'tr', name: 'Turkish', nativeName: 'Türkçe', flag: '🇹🇷' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', flag: '🇨🇳' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦' },
  { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', flag: '🇮🇳' },
  { code: 'uz', name: 'Uzbek', nativeName: 'O\'zbek', flag: '🇺🇿' },
  { code: 'kk', name: 'Kazakh', nativeName: 'Қазақ', flag: '🇰🇿' },
  { code: 'ky', name: 'Kyrgyz', nativeName: 'Кыргыз', flag: '🇰🇬' },
  { code: 'tg', name: 'Tajik', nativeName: 'Тоҷикӣ', flag: '🇹🇯' },
  { code: 'fa', name: 'Dari', nativeName: 'دری', flag: '🇦🇫' },
  
  // New 200+ languages (alphabetically organized)
  { code: 'ab', name: 'Abkhaz', nativeName: 'Аҧсуа', flag: '🌐' },
  { code: 'aa', name: 'Afar', nativeName: 'Afar', flag: '🇪🇹' },
  { code: 'af', name: 'Afrikaans', nativeName: 'Afrikaans', flag: '🇿🇦' },
  { code: 'sq', name: 'Albanian', nativeName: 'Shqip', flag: '🇦🇱' },
  { code: 'alz', name: 'Alur', nativeName: 'Alur', flag: '🌐' },
  { code: 'am', name: 'Amharic', nativeName: 'አማርኛ', flag: '🇪🇹' },
  { code: 'hy', name: 'Armenian', nativeName: 'Հայերեն', flag: '🇦🇲' },
  { code: 'as', name: 'Assamese', nativeName: 'অসমীয়া', flag: '🇮🇳' },
  { code: 'awa', name: 'Awadhi', nativeName: 'अवधी', flag: '🇮🇳' },
  { code: 'av', name: 'Avar', nativeName: 'Авар', flag: '🌐' },
  { code: 'ay', name: 'Aymara', nativeName: 'Aymar aru', flag: '🇧🇴' },
  { code: 'ace', name: 'Acehnese', nativeName: 'Acèh', flag: '🇮🇩' },
  { code: 'ach', name: 'Acholi', nativeName: 'Acholi', flag: '🇺🇬' },
  { code: 'az', name: 'Azerbaijani', nativeName: 'Azərbaycanca', flag: '🇦🇿' },
  { code: 'bm', name: 'Bambara', nativeName: 'Bamanankan', flag: '🇲🇱' },
  { code: 'bal', name: 'Baluchi', nativeName: 'بلوچی', flag: '🇵🇰' },
  { code: 'bci', name: 'Baule', nativeName: 'Baule', flag: '🇨🇮' },
  { code: 'eu', name: 'Basque', nativeName: 'Euskara', flag: '🇪🇸' },
  { code: 'btk', name: 'Batak Karo', nativeName: 'Batak Karo', flag: '🇮🇩' },
  { code: 'bts', name: 'Batak Simalungun', nativeName: 'Batak Simalungun', flag: '🇮🇩' },
  { code: 'bbc', name: 'Batak Toba', nativeName: 'Batak Toba', flag: '🇮🇩' },
  { code: 'be', name: 'Belarusian', nativeName: 'Беларуская', flag: '🇧🇾' },
  { code: 'bem', name: 'Bemba', nativeName: 'Bemba', flag: '🇿🇲' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', flag: '🇧🇩' },
  { code: 'bew', name: 'Betawi', nativeName: 'Betawi', flag: '🇮🇩' },
  { code: 'bik', name: 'Bikol', nativeName: 'Bikol', flag: '🇵🇭' },
  { code: 'my', name: 'Burmese', nativeName: 'မြန်မာဘာသာ', flag: '🇲🇲' },
  { code: 'bg', name: 'Bulgarian', nativeName: 'Български', flag: '🇧🇬' },
  { code: 'bs', name: 'Bosnian', nativeName: 'Bosanski', flag: '🇧🇦' },
  { code: 'ba', name: 'Bashkir', nativeName: 'Башҡорт', flag: '🇷🇺' },
  { code: 'br', name: 'Breton', nativeName: 'Brezhoneg', flag: '🇫🇷' },
  { code: 'bua', name: 'Buryat', nativeName: 'Буряад', flag: '🇷🇺' },
  { code: 'bho', name: 'Bhojpuri', nativeName: 'भोजपुरी', flag: '🇮🇳' },
  { code: 'ca', name: 'Catalan', nativeName: 'Català', flag: '🇪🇸' },
  { code: 'ceb', name: 'Cebuano', nativeName: 'Cebuano', flag: '🇵🇭' },
  { code: 'ch', name: 'Chamorro', nativeName: 'Chamorro', flag: '🇬🇺' },
  { code: 'ce', name: 'Chechen', nativeName: 'Нохчийн', flag: '🇷🇺' },
  { code: 'ny', name: 'Chichewa', nativeName: 'Chichewa', flag: '🇲🇼' },
  { code: 'zh-CN', name: 'Chinese (Simplified)', nativeName: '简体中文', flag: '🇨🇳' },
  { code: 'zh-TW', name: 'Chinese (Traditional)', nativeName: '繁體中文', flag: '🇹🇼' },
  { code: 'chk', name: 'Chuukese', nativeName: 'Chuukese', flag: '🇫🇲' },
  { code: 'cv', name: 'Chuvash', nativeName: 'Чӑваш', flag: '🇷🇺' },
  { code: 'co', name: 'Corsican', nativeName: 'Corsu', flag: '🇫🇷' },
  { code: 'cpf', name: 'Creole (Mauritius)', nativeName: 'Kreol Morisien', flag: '🇲🇺' },
  { code: 'crs', name: 'Creole (Seychelles)', nativeName: 'Kreol Seselwa', flag: '🇸🇨' },
  { code: 'jam', name: 'Creole (Jamaica)', nativeName: 'Patois', flag: '🇯🇲' },
  { code: 'hr', name: 'Croatian', nativeName: 'Hrvatski', flag: '🇭🇷' },
  { code: 'cs', name: 'Czech', nativeName: 'Čeština', flag: '🇨🇿' },
  { code: 'da', name: 'Danish', nativeName: 'Dansk', flag: '🇩🇰' },
  { code: 'prs', name: 'Dari', nativeName: 'دری', flag: '🇦🇫' },
  { code: 'din', name: 'Dinka', nativeName: 'Dinka', flag: '🇸🇸' },
  { code: 'dv', name: 'Divehi', nativeName: 'ދިވެހި', flag: '🇲🇻' },
  { code: 'doi', name: 'Dogri', nativeName: 'डोगरी', flag: '🇮🇳' },
  { code: 'nl', name: 'Dutch', nativeName: 'Nederlands', flag: '🇳🇱' },
  { code: 'dyu', name: 'Dyula', nativeName: 'Dyula', flag: '🇨🇮' },
  { code: 'dz', name: 'Dzongkha', nativeName: 'རྫོང་ཁ', flag: '🇧🇹' },
  { code: 'en-US', name: 'English (US)', nativeName: 'English (US)', flag: '🇺🇸' },
  { code: 'eo', name: 'Esperanto', nativeName: 'Esperanto', flag: '🌐' },
  { code: 'et', name: 'Estonian', nativeName: 'Eesti', flag: '🇪🇪' },
  { code: 'ee', name: 'Ewe', nativeName: 'Eʋegbe', flag: '🇹🇬' },
  { code: 'fo', name: 'Faroese', nativeName: 'Føroyskt', flag: '🇫🇴' },
  { code: 'fj', name: 'Fijian', nativeName: 'Vosa Vakaviti', flag: '🇫🇯' },
  { code: 'tl', name: 'Filipino', nativeName: 'Filipino', flag: '🇵🇭' },
  { code: 'fi', name: 'Finnish', nativeName: 'Suomi', flag: '🇫🇮' },
  { code: 'fon', name: 'Fon', nativeName: 'Fon', flag: '🇧🇯' },
  { code: 'fy', name: 'Frisian', nativeName: 'Frysk', flag: '🇳🇱' },
  { code: 'ff', name: 'Fulani', nativeName: 'Fulfulde', flag: '🌐' },
  { code: 'gaa', name: 'Ga', nativeName: 'Ga', flag: '🇬🇭' },
  { code: 'gl', name: 'Galician', nativeName: 'Galego', flag: '🇪🇸' },
  { code: 'ka', name: 'Georgian', nativeName: 'ქართული', flag: '🇬🇪' },
  { code: 'el', name: 'Greek', nativeName: 'Ελληνικά', flag: '🇬🇷' },
  { code: 'gn', name: 'Guarani', nativeName: 'Guarani', flag: '🇵🇾' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', flag: '🇮🇳' },
  { code: 'ht', name: 'Haitian Creole', nativeName: 'Kreyòl Ayisyen', flag: '🇭🇹' },
  { code: 'cnh', name: 'Haka Chin', nativeName: 'Haka Chin', flag: '🇲🇲' },
  { code: 'ha', name: 'Hausa', nativeName: 'Hausa', flag: '🇳🇬' },
  { code: 'haw', name: 'Hawaiian', nativeName: 'ʻŌlelo Hawaiʻi', flag: '🇺🇸' },
  { code: 'he', name: 'Hebrew', nativeName: 'עברית', flag: '🇮🇱' },
  { code: 'hil', name: 'Hiligaynon', nativeName: 'Hiligaynon', flag: '🇵🇭' },
  { code: 'hmn', name: 'Hmong', nativeName: 'Hmong', flag: '🌐' },
  { code: 'hu', name: 'Hungarian', nativeName: 'Magyar', flag: '🇭🇺' },
  { code: 'hne', name: 'Hunsrik', nativeName: 'Hunsrik', flag: '🇧🇷' },
  { code: 'is', name: 'Icelandic', nativeName: 'Íslenska', flag: '🇮🇸' },
  { code: 'ig', name: 'Igbo', nativeName: 'Igbo', flag: '🇳🇬' },
  { code: 'ilo', name: 'Ilocano', nativeName: 'Ilocano', flag: '🇵🇭' },
  { code: 'id', name: 'Indonesian', nativeName: 'Bahasa Indonesia', flag: '🇮🇩' },
  { code: 'ga', name: 'Irish', nativeName: 'Gaeilge', flag: '🇮🇪' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹' },
  { code: 'iu-Latn', name: 'Inuktut (Latin)', nativeName: 'Inuktut', flag: '🇨🇦' },
  { code: 'iu-Cans', name: 'Inuktut (Syllabics)', nativeName: 'ᐃᓄᒃᑎᑐᑦ', flag: '🇨🇦' },
  { code: 'iba', name: 'Iban', nativeName: 'Iban', flag: '🇲🇾' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵' },
  { code: 'jw', name: 'Javanese', nativeName: 'Basa Jawa', flag: '🇮🇩' },
  { code: 'kl', name: 'Kalaallisut', nativeName: 'Kalaallisut', flag: '🇬🇱' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', flag: '🇮🇳' },
  { code: 'yue', name: 'Cantonese', nativeName: '粵語', flag: '🇭🇰' },
  { code: 'kr', name: 'Kanuri', nativeName: 'Kanuri', flag: '🇳🇬' },
  { code: 'pam', name: 'Kapampangan', nativeName: 'Kapampangan', flag: '🇵🇭' },
  { code: 'kek', name: 'Kekchi', nativeName: 'Q\'eqchi\'', flag: '🇬🇹' },
  { code: 'kha', name: 'Khasi', nativeName: 'Khasi', flag: '🇮🇳' },
  { code: 'km', name: 'Khmer', nativeName: 'ភាសាខ្មែរ', flag: '🇰🇭' },
  { code: 'rw', name: 'Kinyarwanda', nativeName: 'Ikinyarwanda', flag: '🇷🇼' },
  { code: 'kig', name: 'Kiga', nativeName: 'Rukiga', flag: '🇺🇬' },
  { code: 'kg', name: 'Kikongo', nativeName: 'Kikongo', flag: '🇨🇩' },
  { code: 'ktu', name: 'Kituba', nativeName: 'Kituba', flag: '🇨🇩' },
  { code: 'kok', name: 'Konkani', nativeName: 'कोंकणी', flag: '🇮🇳' },
  { code: 'ko', name: 'Korean', nativeName: '한국어', flag: '🇰🇷' },
  { code: 'kri', name: 'Krio', nativeName: 'Krio', flag: '🇸🇱' },
  { code: 'ku', name: 'Kurdish (Kurmanji)', nativeName: 'Kurdî', flag: '🌐' },
  { code: 'ckb', name: 'Kurdish (Sorani)', nativeName: 'کوردی', flag: '🇮🇶' },
  { code: 'kv', name: 'Komi', nativeName: 'Коми', flag: '🇷🇺' },
  { code: 'lo', name: 'Lao', nativeName: 'ລາວ', flag: '🇱🇦' },
  { code: 'la', name: 'Latin', nativeName: 'Latina', flag: '🌐' },
  { code: 'ltg', name: 'Latgalian', nativeName: 'Latgalīšu', flag: '🇱🇻' },
  { code: 'lv', name: 'Latvian', nativeName: 'Latviešu', flag: '🇱🇻' },
  { code: 'lij', name: 'Ligurian', nativeName: 'Ligure', flag: '🇮🇹' },
  { code: 'li', name: 'Limburgish', nativeName: 'Limburgs', flag: '🇳🇱' },
  { code: 'ln', name: 'Lingala', nativeName: 'Lingála', flag: '🇨🇩' },
  { code: 'lt', name: 'Lithuanian', nativeName: 'Lietuvių', flag: '🇱🇹' },
  { code: 'lmo', name: 'Lombard', nativeName: 'Lombard', flag: '🇮🇹' },
  { code: 'lg', name: 'Luganda', nativeName: 'Luganda', flag: '🇺��' },
  { code: 'luo', name: 'Luo', nativeName: 'Dholuo', flag: '🇰🇪' },
  { code: 'lb', name: 'Luxembourgish', nativeName: 'Lëtzebuergesch', flag: '🇱🇺' },
  { code: 'mk', name: 'Macedonian', nativeName: 'Македонски', flag: '🇲🇰' },
  { code: 'mad', name: 'Madurese', nativeName: 'Madhurâ', flag: '🇮🇩' },
  { code: 'mak', name: 'Makassar', nativeName: 'Makassar', flag: '🇮🇩' },
  { code: 'mg', name: 'Malagasy', nativeName: 'Malagasy', flag: '🇲🇬' },
  { code: 'ms', name: 'Malay', nativeName: 'Bahasa Melayu', flag: '🇲🇾' },
  { code: 'ms-Arab', name: 'Malay (Jawi)', nativeName: 'بهاس ملايو', flag: '🇲🇾' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം', flag: '🇮🇳' },
  { code: 'mt', name: 'Maltese', nativeName: 'Malti', flag: '🇲🇹' },
  { code: 'mam', name: 'Mam', nativeName: 'Mam', flag: '🇬🇹' },
  { code: 'gv', name: 'Manx', nativeName: 'Gaelg', flag: '🇮🇲' },
  { code: 'mi', name: 'Maori', nativeName: 'Te Reo Māori', flag: '🇳🇿' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', flag: '🇮🇳' },
  { code: 'mh', name: 'Marshallese', nativeName: 'Kajin M̧ajeļ', flag: '🇲🇭' },
  { code: 'mwr', name: 'Marwadi', nativeName: 'मारवाड़ी', flag: '🇮🇳' },
  { code: 'mai', name: 'Maithili', nativeName: 'मैथिली', flag: '🇮🇳' },
  { code: 'mni', name: 'Meiteilon (Manipuri)', nativeName: 'মৈতৈলোন্', flag: '🇮🇳' },
  { code: 'min', name: 'Minangkabau', nativeName: 'Minangkabau', flag: '🇮🇩' },
  { code: 'lus', name: 'Mizo', nativeName: 'Mizo ṭawng', flag: '🇮🇳' },
  { code: 'mn', name: 'Mongolian', nativeName: 'Монгол', flag: '🇲🇳' },
  { code: 'nhe', name: 'Nahuatl (Eastern Huasteca)', nativeName: 'Nahuatl', flag: '🇲🇽' },
  { code: 'ndc', name: 'Ndau', nativeName: 'Ndau', flag: '🇿🇼' },
  { code: 'nr', name: 'Ndebele (South)', nativeName: 'isiNdebele', flag: '🇿🇦' },
  { code: 'ne', name: 'Nepali', nativeName: 'नेपाली', flag: '🇳🇵' },
  { code: 'new', name: 'Nepalbhasa (Newari)', nativeName: 'नेपाल भाषा', flag: '🇳🇵' },
  { code: 'nqo', name: 'NKo', nativeName: 'ߒߞߏ', flag: '🌐' },
  { code: 'no', name: 'Norwegian', nativeName: 'Norsk', flag: '🇳🇴' },
  { code: 'nus', name: 'Nuer', nativeName: 'Thok Naath', flag: '🇸🇸' },
  { code: 'or', name: 'Odiya (Oriya)', nativeName: 'ଓଡ଼ିଆ', flag: '🇮🇳' },
  { code: 'oc', name: 'Occitan', nativeName: 'Occitan', flag: '🇫🇷' },
  { code: 'om', name: 'Oromo', nativeName: 'Oromoo', flag: '🇪🇹' },
  { code: 'os', name: 'Ossetian', nativeName: 'Ирон', flag: '🇷🇺' },
  { code: 'pag', name: 'Pangasinan', nativeName: 'Pangasinan', flag: '🇵🇭' },
  { code: 'pa', name: 'Punjabi (Gurmukhi)', nativeName: 'ਪੰਜਾਬੀ', flag: '🇮🇳' },
  { code: 'ps', name: 'Pashto', nativeName: 'پښتو', flag: '🇦🇫' },
  { code: 'fa-AF', name: 'Persian', nativeName: 'فارسی', flag: '🇮🇷' },
  { code: 'pl', name: 'Polish', nativeName: 'Polski', flag: '🇵🇱' },
  { code: 'pt-BR', name: 'Portuguese (Brazil)', nativeName: 'Português (Brasil)', flag: '🇧🇷' },
  { code: 'pt-PT', name: 'Portuguese (Portugal)', nativeName: 'Português (Portugal)', flag: '🇵🇹' },
  { code: 'pap', name: 'Papiamento', nativeName: 'Papiamento', flag: '🇦🇼' },
  { code: 'qu', name: 'Quechua', nativeName: 'Runasimi', flag: '🇵🇪' },
  { code: 'ro', name: 'Romanian', nativeName: 'Română', flag: '🇷🇴' },
  { code: 'rm', name: 'Romansh', nativeName: 'Rumantsch', flag: '🇨🇭' },
  { code: 'rn', name: 'Rundi', nativeName: 'Kirundi', flag: '🇧🇮' },
  { code: 'sm', name: 'Samoan', nativeName: 'Gagana Sāmoa', flag: '🇼🇸' },
  { code: 'sg', name: 'Sango', nativeName: 'Sängö', flag: '🇨🇫' },
  { code: 'sa', name: 'Sanskrit', nativeName: 'संस्कृतम्', flag: '🇮🇳' },
  { code: 'sat-Latn', name: 'Santal (Latin)', nativeName: 'Santali', flag: '🇮🇳' },
  { code: 'sat-Olck', name: 'Santal (Ol Chiki)', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ', flag: '🇮🇳' },
  { code: 'gd', name: 'Scottish Gaelic', nativeName: 'Gàidhlig', flag: '🏴' },
  { code: 'nso', name: 'Sepedi', nativeName: 'Sepedi', flag: '🇿🇦' },
  { code: 'sr', name: 'Serbian', nativeName: 'Српски', flag: '🇷🇸' },
  { code: 'st', name: 'Sesotho', nativeName: 'Sesotho', flag: '🇱🇸' },
  { code: 'shn', name: 'Shan', nativeName: 'လိၵ်ႈတႆး', flag: '🇲🇲' },
  { code: 'sn', name: 'Shona', nativeName: 'chiShona', flag: '🇿🇼' },
  { code: 'scn', name: 'Sicilian', nativeName: 'Sicilianu', flag: '🇮🇹' },
  { code: 'szl', name: 'Silesian', nativeName: 'Ślōnskŏ', flag: '🇵🇱' },
  { code: 'sd', name: 'Sindhi', nativeName: 'سنڌي', flag: '🇵🇰' },
  { code: 'si', name: 'Sinhala', nativeName: 'සිංහල', flag: '🇱🇰' },
  { code: 'sk', name: 'Slovak', nativeName: 'Slovenčina', flag: '🇸🇰' },
  { code: 'sl', name: 'Slovenian', nativeName: 'Slovenščina', flag: '🇸🇮' },
  { code: 'so', name: 'Somali', nativeName: 'Soomaali', flag: '🇸🇴' },
  { code: 'se', name: 'Sami (Northern)', nativeName: 'Davvisámegiella', flag: '🇳🇴' },
  { code: 'su', name: 'Sundanese', nativeName: 'Basa Sunda', flag: '🇮🇩' },
  { code: 'sus', name: 'Susu', nativeName: 'Susu', flag: '🇬🇳' },
  { code: 'sw', name: 'Swahili', nativeName: 'Kiswahili', flag: '🇹🇿' },
  { code: 'ss', name: 'Swati', nativeName: 'siSwati', flag: '🇸��' },
  { code: 'sv', name: 'Swedish', nativeName: 'Svenska', flag: '🇸🇪' },
  { code: 'ty', name: 'Tahitian', nativeName: 'Reo Tahiti', flag: '🇵🇫' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', flag: '🇮🇳' },
  { code: 'tt', name: 'Tatar', nativeName: 'Татар', flag: '🇷🇺' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', flag: '🇮🇳' },
  { code: 'tet', name: 'Tetum', nativeName: 'Tetun', flag: '🇹🇱' },
  { code: 'th', name: 'Thai', nativeName: 'ไทย', flag: '🇹🇭' },
  { code: 'bo', name: 'Tibetan', nativeName: 'བོད་སྐད་', flag: '🌐' },
  { code: 'ti', name: 'Tigrinya', nativeName: 'ትግርኛ', flag: '🇪🇷' },
  { code: 'tiv', name: 'Tiv', nativeName: 'Tiv', flag: '🇳🇬' },
  { code: 'tpi', name: 'Tok Pisin', nativeName: 'Tok Pisin', flag: '🇵🇬' },
  { code: 'to', name: 'Tongan', nativeName: 'Lea Faka-Tonga', flag: '🇹🇴' },
  { code: 'ts', name: 'Tsonga', nativeName: 'Xitsonga', flag: '🇿🇦' },
  { code: 'tn', name: 'Tswana', nativeName: 'Setswana', flag: '🇧🇼' },
  { code: 'tcy', name: 'Tulu', nativeName: 'ತುಳು', flag: '🇮🇳' },
  { code: 'tum', name: 'Tumbuka', nativeName: 'Chitumbuka', flag: '🇲🇼' },
  { code: 'tk', name: 'Turkmen', nativeName: 'Türkmençe', flag: '🇹🇲' },
  { code: 'tyv', name: 'Tuvan', nativeName: 'Тыва', flag: '🇷🇺' },
  { code: 'tw', name: 'Twi', nativeName: 'Twi', flag: '🇬🇭' },
  { code: 'uk', name: 'Ukrainian', nativeName: 'Українська', flag: '🇺🇦' },
  { code: 'udm', name: 'Udmurt', nativeName: 'Удмурт', flag: '🇷🇺' },
  { code: 'ur', name: 'Urdu', nativeName: 'اردو', flag: '🇵🇰' },
  { code: 'ug', name: 'Uyghur', nativeName: 'ئۇيغۇرچە', flag: '🌐' },
  { code: 've', name: 'Venda', nativeName: 'Tshivenḓa', flag: '🇿🇦' },
  { code: 'vec', name: 'Venetian', nativeName: 'Vèneto', flag: '🇮🇹' },
  { code: 'vi', name: 'Vietnamese', nativeName: 'Tiếng Việt', flag: '🇻🇳' },
  { code: 'cy', name: 'Welsh', nativeName: 'Cymraeg', flag: '🏴' },
  { code: 'war', name: 'Waray', nativeName: 'Winaray', flag: '🇵🇭' },
  { code: 'wo', name: 'Wolof', nativeName: 'Wolof', flag: '🇸🇳' },
  { code: 'xh', name: 'Xhosa', nativeName: 'isiXhosa', flag: '🇿🇦' },
  { code: 'sah', name: 'Yakut', nativeName: 'Саха', flag: '🇷🇺' },
  { code: 'yi', name: 'Yiddish', nativeName: 'ייִדיש', flag: '🌐' },
  { code: 'yo', name: 'Yoruba', nativeName: 'Yorùbá', flag: '🇳🇬' },
  { code: 'yua', name: 'Yucatec Maya', nativeName: 'Màaya T\'àan', flag: '🇲🇽' },
  { code: 'zap', name: 'Zapotec', nativeName: 'Zapoteco', flag: '🇲🇽' },
  { code: 'zu', name: 'Zulu', nativeName: 'isiZulu', flag: '🇿🇦' },
  { code: 'mhr', name: 'Meadow Mari', nativeName: 'Олык марий', flag: '🇷🇺' },
  { code: 'tzm', name: 'Tamazight', nativeName: 'Tamaziɣt', flag: '🇲🇦' },
  { code: 'tzm-Tfng', name: 'Tamazight (Tifinagh)', nativeName: 'ⵜⴰⵎⴰⵣⵉⵖⵜ', flag: '🇲🇦' },
  { code: 'lua', name: 'Luba-Kasai', nativeName: 'Tshiluba', flag: '🇨🇩' },
];

export const mockChats: Chat[] = [
  {
    id: '1',
    userId: 'farmer1',
    userName: 'John Farmer',
    userAvatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop',
    productId: '1',
    productName: 'Fresh Organic Tomatoes',
    productImage: 'https://images.unsplash.com/photo-1546470427-e26264be0b6e?w=400&h=300&fit=crop',
    lastMessage: 'The tomatoes are ready for pickup tomorrow morning!',
    lastMessageTime: '10:30 AM',
    unreadCount: 2,
    orderStatus: 'confirmed',
    messages: [
      {
        id: 'm1',
        senderId: 'farmer1',
        text: 'Hello! Thank you for your order.',
        timestamp: '10:15 AM'
      },
      {
        id: 'm2',
        senderId: 'me',
        text: 'When can I pick up the tomatoes?',
        timestamp: '10:20 AM'
      },
      {
        id: 'm3',
        senderId: 'farmer1',
        text: 'The tomatoes are ready for pickup tomorrow morning!',
        timestamp: '10:30 AM'
      }
    ]
  },
  {
    id: '2',
    userId: 'farmer2',
    userName: 'Maria Garcia',
    userAvatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop',
    productId: '2',
    productName: 'Premium Wheat Grain',
    productImage: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&h=300&fit=crop',
    lastMessage: 'Your order is on the way! Expected delivery: 2 hours',
    lastMessageTime: 'Yesterday',
    unreadCount: 0,
    orderStatus: 'in-transit',
    messages: [
      {
        id: 'm1',
        senderId: 'farmer2',
        text: 'Your order has been shipped!',
        timestamp: 'Yesterday 3:00 PM'
      },
      {
        id: 'm2',
        senderId: 'farmer2',
        text: 'Your order is on the way! Expected delivery: 2 hours',
        timestamp: 'Yesterday 4:30 PM'
      }
    ]
  },
  {
    id: '3',
    userId: 'farmer3',
    userName: 'Ahmed Hassan',
    userAvatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop',
    productId: '3',
    productName: 'Fresh Carrots',
    productImage: 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=400&h=300&fit=crop',
    lastMessage: 'Order delivered successfully. Thank you!',
    lastMessageTime: 'Jan 15',
    unreadCount: 0,
    orderStatus: 'delivered',
    messages: [
      {
        id: 'm1',
        senderId: 'farmer3',
        text: 'Your carrots are being prepared',
        timestamp: 'Jan 14, 10:00 AM'
      },
      {
        id: 'm2',
        senderId: 'farmer3',
        text: 'Order delivered successfully. Thank you!',
        timestamp: 'Jan 15, 2:00 PM'
      }
    ]
  },
  {
    id: '4',
    userId: 'farmer4',
    userName: 'Lina Popova',
    userAvatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop',
    lastMessage: 'Do you have potatoes in stock?',
    lastMessageTime: '2 days ago',
    unreadCount: 1,
    messages: [
      {
        id: 'm1',
        senderId: 'me',
        text: 'Do you have potatoes in stock?',
        timestamp: '2 days ago'
      }
    ]
  },
  {
    id: '5',
    userId: 'support',
    userName: 'UDX Support',
    userAvatar: 'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=100&h=100&fit=crop',
    lastMessage: 'How can we help you today?',
    lastMessageTime: 'Jan 10',
    unreadCount: 0,
    messages: [
      {
        id: 'm1',
        senderId: 'support',
        text: 'Welcome to UDX Support! How can we help you today?',
        timestamp: 'Jan 10, 9:00 AM'
      }
    ]
  },
  {
    id: '6',
    userId: 'farmer5',
    userName: 'Chen Wei',
    userAvatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop',
    productId: '4',
    productName: 'Organic Rice',
    productImage: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
    lastMessage: 'Payment confirmed. Preparing your order now.',
    lastMessageTime: 'Jan 18',
    unreadCount: 0,
    orderStatus: 'pending',
    messages: [
      {
        id: 'm1',
        senderId: 'me',
        text: 'I would like to order 50kg of rice',
        timestamp: 'Jan 18, 11:00 AM'
      },
      {
        id: 'm2',
        senderId: 'farmer5',
        text: 'Payment confirmed. Preparing your order now.',
        timestamp: 'Jan 18, 11:30 AM'
      }
    ]
  }
];