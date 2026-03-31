# OpenWeatherMap API Setup

## Get Your Free API Key

1. **Sign up** at https://openweathermap.org/api
2. **Create an account** (it's free)
3. **Navigate to API Keys** in your account dashboard
4. **Copy your API key**

## Add to Your Environment

Open `/Users/shayxnazar/Downloads/Bank fayllar/UDX (2)/backend/.env` and add:

```bash
OPENWEATHER_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with the actual API key you copied.

## Restart the Backend

After adding the API key, restart your backend server:

```bash
# Stop the current server (Ctrl+C in the terminal)
# Then restart:
cd "/Users/shayxnazar/Downloads/Bank fayllar/UDX (2)"
python3 -m uvicorn backend.main:app --reload
```

## Test the Weather Feature

1. Open the app at http://localhost:3000
2. Allow location access when prompted
3. The weather card should display your local weather data

**Note**: The free tier allows 60 calls/minute and 1,000,000 calls/month, which is more than enough for development and testing.
