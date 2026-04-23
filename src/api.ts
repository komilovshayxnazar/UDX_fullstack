import { Product, Order } from './data/mockData';

export interface User {
    id: string;
    phone: string;
    role: 'buyer' | 'seller';
    name?: string;
    avatar?: string;
}

const API_URL = 'https://udx-marketplace.store';

export const api = {
    // Auth
    async login(phone: string, password?: string): Promise<{ access_token: string; token_type: string }> {
        const formData = new URLSearchParams();
        formData.append('username', phone);
        formData.append('password', password || 'password'); // Mock password for OTP flow if needed, or handle differently

        const response = await fetch(`${API_URL}/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });

        if (!response.ok) throw new Error('Login failed');
        return response.json();
    },

    async requestTelegramOtp(telegramUsername: string): Promise<void> {
        const response = await fetch(`${API_URL}/auth/otp/request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_username: telegramUsername }),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to send OTP');
        }
    },

    async verifyTelegramOtp(telegramUsername: string, code: string): Promise<void> {
        const response = await fetch(`${API_URL}/auth/otp/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_username: telegramUsername, code }),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Invalid OTP');
        }
    },

    async register(user: { phone: string; password?: string; name?: string; role?: string }) {
        const response = await fetch(`${API_URL}/users/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                phone: user.phone,
                password: user.password || 'password',
                name: user.name,
                role: user.role || 'buyer'
            }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Registration failed');
        }
        return response.json();
    },

    async getMe(token: string): Promise<User> {
        const response = await fetch(`${API_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch user');
        return response.json();
    },

    // Balance
    async depositBalance(amount: number, token: string): Promise<User> {
        const response = await fetch(`${API_URL}/users/me/balance/deposit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ amount }),
        });
        if (!response.ok) throw new Error('Failed to deposit balance');
        return response.json();
    },

    async withdrawBalance(amount: number, token: string): Promise<User> {
        const response = await fetch(`${API_URL}/users/me/balance/withdraw`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ amount }),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to withdraw balance');
        }
        return response.json();
    },

    // Products
    async getProducts(): Promise<Product[]> {
        const response = await fetch(`${API_URL}/products/`);
        if (!response.ok) throw new Error('Failed to fetch products');
        const data = await response.json();
        return data.map((p: any) => ({
            ...p,
            id: p.id,
            name: p.name,
            price: p.price,
            unit: p.unit,
            image: p.image,
            farmerId: p.seller_id,
            farmerName: 'Local Farmer',
            description: p.description,
            category: p.category_id,
            rating: p.rating,
            reviewCount: p.review_count,
            distance: 2.5, // Mock distance
            certified: p.certified,
            inStock: p.in_stock,
            gallery: p.gallery || [],
            views: p.views,
            sales: p.sales
        }));
    },

    async createProduct(product: any, token: string): Promise<Product> {
        const response = await fetch(`${API_URL}/products/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(product),
        });
        if (!response.ok) throw new Error('Failed to create product');
        return response.json();
    },

    // Weather
    async getWeather(lat: number, lon: number): Promise<any> {
        const response = await fetch(`${API_URL}/weather?lat=${lat}&lon=${lon}`);
        if (!response.ok) throw new Error('Failed to fetch weather data');
        return response.json();
    },

    // Orders
    async createOrder(order: any, token: string): Promise<Order> {
        const response = await fetch(`${API_URL}/orders/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(order),
        });
        if (!response.ok) throw new Error('Failed to create order');
        return response.json();
    },

    async getOrders(token: string): Promise<Order[]> {
        const response = await fetch(`${API_URL}/orders/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch orders');
        return response.json();
    },

    // Google OAuth
    async getGoogleAuthUrl(): Promise<{ auth_url: string }> {
        const response = await fetch(`${API_URL}/auth/google/login`);
        if (!response.ok) throw new Error('Failed to get Google auth URL');
        return response.json();
    },

    async loginWithGoogle(): Promise<void> {
        const { auth_url } = await this.getGoogleAuthUrl();
        // Open Google OAuth in the same window
        window.location.href = auth_url;
    },

    async getGoogleRegisterUrl(): Promise<{ auth_url: string }> {
        const response = await fetch(`${API_URL}/auth/google/register`);
        if (!response.ok) throw new Error('Failed to get Google register URL');
        return response.json();
    },

    async registerWithGoogle(): Promise<void> {
        const { auth_url } = await this.getGoogleRegisterUrl();
        // Open Google OAuth registration in the same window
        window.location.href = auth_url;
    },

    // User Profile
    async getCurrentUser(token: string): Promise<any> {
        const response = await fetch(`${API_URL}/users/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch user data');
        return response.json();
    },

    async updateProfile(data: { name?: string; avatar?: string; description?: string }, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('Failed to update profile');
        return response.json();
    },

    async changePassword(data: { current_password: string; new_password: string }, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/users/me/password`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to change password');
        }
        return response.json();
    },

    async changePhone(data: { new_phone: string; password: string }, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/users/me/phone`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to change phone number');
        }
        return response.json();
    },

    async update2FA(is_2fa_enabled: boolean, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/users/me/2fa`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ is_2fa_enabled }),
        });
        if (!response.ok) throw new Error('Failed to update 2FA settings');
        return response.json();
    },

    // Messaging/Chats
    async getChats(token: string): Promise<any[]> {
        const response = await fetch(`${API_URL}/chats/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch chats');
        return response.json();
    },

    async getChatMessages(chatId: string, token: string): Promise<any[]> {
        const response = await fetch(`${API_URL}/chats/${chatId}/messages`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch messages');
        return response.json();
    },

    async sendMessage(chatId: string, messageText: string, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/chats/${chatId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ message_text: messageText }),
        });
        if (!response.ok) throw new Error('Failed to send message');
        return response.json();
    },

    async markChatAsRead(chatId: string, token: string): Promise<any> {
        const response = await fetch(`${API_URL}/chats/${chatId}/mark-read`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to mark chat as read');
        return response.json();
    },

    async createChat(otherUserId: string, productId: string | null, initialMessage: string | null, token: string): Promise<{ chat_id: string; existing: boolean }> {
        const response = await fetch(`${API_URL}/chats/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                other_user_id: otherUserId,
                product_id: productId,
                initial_message: initialMessage
            }),
        });
        if (!response.ok) throw new Error('Failed to create chat');
        return response.json();
    }
};
