import asyncio
import json
import requests
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.models import SubscriptionTier

class WeatherMCPServer:
    """MCP Server for real-time weather information using OpenWeatherMap API"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY', 'demo_key')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.tools = {
            "get_current_weather": self._get_current_weather,
            "get_weather_forecast": self._get_weather_forecast,
            "get_weather_alerts": self._get_weather_alerts
        }

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP weather tool with real API data"""
        if tool_name not in self.tools:
            return {"error": f"Weather tool {tool_name} not found"}
        
        try:
            return await self.tools[tool_name](arguments)
        except Exception as e:
            return {"error": f"Weather API error: {str(e)}"}

    def _get_coordinates(self, location: str) -> Optional[Dict[str, float]]:
        """Get coordinates for location using geocoding API"""
        try:
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={self.api_key}"
            response = requests.get(geo_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {"lat": data[0]["lat"], "lon": data[0]["lon"]}
            return None
        except Exception:
            return None

    async def _get_current_weather(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get real-time current weather for a location"""
        location = args.get("location", "New York")
        
        # Get coordinates first
        coords = self._get_coordinates(location)
        if not coords:
            return {"error": f"Location '{location}' not found"}
        
        try:
            # Call OpenWeatherMap current weather API
            weather_url = f"{self.base_url}/weather?lat={coords['lat']}&lon={coords['lon']}&appid={self.api_key}&units=metric"
            response = requests.get(weather_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather_data = {
                    "location": f"{data['name']}, {data['sys']['country']}",
                    "temperature": f"{data['main']['temp']:.1f}°C",
                    "condition": data['weather'][0]['description'].title(),
                    "humidity": f"{data['main']['humidity']}%",
                    "wind_speed": f"{data['wind']['speed']} m/s",
                    "visibility": f"{data.get('visibility', 0) / 1000:.1f} km",
                    "pressure": f"{data['main']['pressure']} hPa",
                    "feels_like": f"{data['main']['feels_like']:.1f}°C",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                return {"result": {"current_weather": weather_data}}
            else:
                return {"error": f"Weather API returned status {response.status_code}"}
                
        except requests.RequestException as e:
            return {"error": f"Failed to fetch weather data: {str(e)}"}

    async def _get_weather_forecast(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get real-time weather forecast for a location"""
        location = args.get("location", "New York")
        days = min(args.get("days", 3), 5)  # OpenWeatherMap free tier supports 5 days
        
        coords = self._get_coordinates(location)
        if not coords:
            return {"error": f"Location '{location}' not found"}
        
        try:
            # Call OpenWeatherMap 5-day forecast API
            forecast_url = f"{self.base_url}/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={self.api_key}&units=metric"
            response = requests.get(forecast_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Process forecast data (group by day)
                daily_forecasts = {}
                for item in data['list'][:days * 8]:  # 8 forecasts per day (3-hour intervals)
                    date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                    if date not in daily_forecasts:
                        daily_forecasts[date] = {
                            "date": date,
                            "high": item['main']['temp_max'],
                            "low": item['main']['temp_min'],
                            "condition": item['weather'][0]['description'].title()
                        }
                    else:
                        daily_forecasts[date]['high'] = max(daily_forecasts[date]['high'], item['main']['temp_max'])
                        daily_forecasts[date]['low'] = min(daily_forecasts[date]['low'], item['main']['temp_min'])
                
                forecast_list = []
                for date_key in sorted(daily_forecasts.keys())[:days]:
                    forecast = daily_forecasts[date_key]
                    forecast_list.append({
                        "date": forecast['date'],
                        "high": f"{forecast['high']:.1f}°C",
                        "low": f"{forecast['low']:.1f}°C",
                        "condition": forecast['condition']
                    })
                
                forecast_data = {
                    "location": f"{data['city']['name']}, {data['city']['country']}",
                    "forecast": forecast_list
                }
                
                return {"result": {"weather_forecast": forecast_data}}
            else:
                return {"error": f"Forecast API returned status {response.status_code}"}
                
        except requests.RequestException as e:
            return {"error": f"Failed to fetch forecast data: {str(e)}"}

    async def _get_weather_alerts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get real-time weather alerts for a location"""
        location = args.get("location", "New York")
        
        coords = self._get_coordinates(location)
        if not coords:
            return {"error": f"Location '{location}' not found"}
        
        try:
            # Call OpenWeatherMap One Call API for alerts (requires subscription)
            alerts_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={coords['lat']}&lon={coords['lon']}&appid={self.api_key}"
            response = requests.get(alerts_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                alerts = data.get('alerts', [])
                
                alerts_data = {
                    "location": location,
                    "alerts": []
                }
                
                for alert in alerts:
                    alerts_data['alerts'].append({
                        "type": alert.get('event', 'Weather Alert'),
                        "severity": "High" if 'warning' in alert.get('event', '').lower() else "Moderate",
                        "description": alert.get('description', 'Weather alert active'),
                        "valid_from": datetime.fromtimestamp(alert.get('start', 0)).strftime('%Y-%m-%d %H:%M'),
                        "valid_until": datetime.fromtimestamp(alert.get('end', 0)).strftime('%Y-%m-%d %H:%M')
                    })
                
                return {"result": {"weather_alerts": alerts_data}}
            else:
                # Fallback for free tier - no alerts available
                return {"result": {"weather_alerts": {"location": location, "alerts": [], "note": "Weather alerts require premium API access"}}}
                
        except requests.RequestException as e:
            return {"error": f"Failed to fetch alerts data: {str(e)}"}

class WeatherMCPClient:
    """Client for weather MCP server"""
    
    def __init__(self):
        self.server = WeatherMCPServer()

    async def execute_weather_tool(self, tool_name: str, arguments: Dict[str, Any], tier: SubscriptionTier) -> Dict[str, Any]:
        """Execute weather MCP tool based on subscription tier"""
        
        # Weather tools available for Advanced and Premium tiers
        if tier == SubscriptionTier.BASIC:
            return {"error": "Weather tools require Advanced or Premium subscription"}
        
        # Premium users get all weather tools
        if tier == SubscriptionTier.PREMIUM:
            return await self.server.call_tool(tool_name, arguments)
        
        # Advanced users get basic weather tools only
        if tier == SubscriptionTier.ADVANCED:
            if tool_name in ["get_current_weather", "get_weather_forecast"]:
                return await self.server.call_tool(tool_name, arguments)
            else:
                return {"error": f"Weather tool {tool_name} requires Premium subscription"}
        
        return {"error": "Invalid subscription tier"}

    async def get_available_weather_tools(self, tier: SubscriptionTier) -> List[str]:
        """Get available weather tools for subscription tier"""
        if tier == SubscriptionTier.BASIC:
            return []
        elif tier == SubscriptionTier.ADVANCED:
            return ["get_current_weather", "get_weather_forecast"]
        elif tier == SubscriptionTier.PREMIUM:
            return list(self.server.tools.keys())
        
        return []