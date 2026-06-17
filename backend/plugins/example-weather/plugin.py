"""Example Weather Plugin — Demonstrates MiLyfe Brain plugin architecture."""

from models.schemas import PermissionLevel


async def get_weather(city: str = "New York") -> str:
    """Get weather for a city (example - returns mock data)."""
    # In a real plugin, this would call a weather API
    return f"Weather in {city}: 72F, Partly Cloudy, Humidity: 45%"


def register(registry):
    """Register plugin tools with the tool registry."""
    registry.register(
        name="get_weather",
        handler=get_weather,
        category="Plugin",
        description="Get weather for a city (example plugin)",
        parameters={"city": "str"},
        permission=PermissionLevel.FREE,
    )


def unregister():
    """Cleanup when plugin is unloaded."""
    pass
