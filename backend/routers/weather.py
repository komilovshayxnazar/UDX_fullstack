from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter(tags=["weather"])

@router.get("/weather")
async def get_weather(lat: float, lon: float):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=500, detail="Weather API key not configured")
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch weather data")
        
        data = response.json()
        
        return {
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "location": data["name"],
            "country": data["sys"]["country"]
        }
