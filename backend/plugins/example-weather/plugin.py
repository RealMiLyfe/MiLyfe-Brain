"""Example weather plugin for MiLyfe Brain."""

import json
from datetime import datetime

try:
    from plugins.loader import PluginBase
except ImportError:
    from backend.plugins.loader import PluginBase


class WeatherPlugin(PluginBase):
    """Example plugin that provides weather information (mock data)."""
    
    async def on_load(self):
        """Initialize the plugin."""
        self.logger.info("Weather plugin loaded")
    
    async def on_unload(self):
        """Cleanup."""
        self.logger.info("Weather plugin unloaded")
    
    async def get_weather(self, location: str = "New York") -> str:
        """Get weather for a location (mock implementation).
        
        In a real plugin, this would call a weather API.
        """
        # Mock weather data
        weather_data = {
            "location": location,
            "temperature": 72,
            "unit": "F",
            "condition": "Partly Cloudy",
            "humidity": 45,
            "wind_speed": 8,
            "wind_direction": "NW",
            "forecast": "Clear skies expected later today",
            "updated_at": datetime.utcnow().isoformat(),
            "note": "This is mock data from the example plugin",
        }
        return json.dumps(weather_data, indent=2)
