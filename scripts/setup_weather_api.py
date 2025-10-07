#!/usr/bin/env python3
"""
Setup script for OpenWeatherMap API integration
Helps users configure real-time weather data for MCP tools
"""

import os
import requests
from typing import Optional

def test_weather_api(api_key: str) -> bool:
    """Test if the OpenWeatherMap API key works"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={api_key}"
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def setup_weather_api():
    """Interactive setup for OpenWeatherMap API"""
    print("🌤️  Setting up Real-time Weather API for MCP Tools")
    print("=" * 50)
    
    print("\n1. Get your FREE OpenWeatherMap API key:")
    print("   • Visit: https://openweathermap.org/api")
    print("   • Sign up for a free account")
    print("   • Go to API Keys section")
    print("   • Copy your API key")
    
    print("\n2. Free tier includes:")
    print("   • Current weather data")
    print("   • 5-day weather forecast")
    print("   • 1,000 API calls/day")
    
    api_key = input("\n3. Enter your OpenWeatherMap API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting...")
        return
    
    print("\n🔍 Testing API key...")
    if test_weather_api(api_key):
        print("✅ API key works! Setting up environment...")
        
        # Update .env file
        env_file = ".env"
        env_content = []
        
        # Read existing .env if it exists
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_content = f.readlines()
        
        # Update or add OPENWEATHER_API_KEY
        updated = False
        for i, line in enumerate(env_content):
            if line.startswith('OPENWEATHER_API_KEY='):
                env_content[i] = f'OPENWEATHER_API_KEY={api_key}\n'
                updated = True
                break
        
        if not updated:
            env_content.append(f'OPENWEATHER_API_KEY={api_key}\n')
        
        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(env_content)
        
        print(f"✅ API key saved to {env_file}")
        print("\n🚀 Weather MCP tools are now ready!")
        print("\nTest weather queries:")
        print("   • 'What's the weather in London?'")
        print("   • 'Show me the forecast for New York'")
        print("   • 'Any weather alerts for Tokyo?'")
        
    else:
        print("❌ API key test failed. Please check:")
        print("   • API key is correct")
        print("   • Internet connection is working")
        print("   • API key is activated (may take a few minutes)")

def check_weather_setup() -> bool:
    """Check if weather API is properly configured"""
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key or api_key == 'your-openweathermap-api-key':
        return False
    
    return test_weather_api(api_key)

if __name__ == "__main__":
    setup_weather_api()