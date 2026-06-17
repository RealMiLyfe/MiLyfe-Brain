"""Example Weather Plugin — Demonstrates plugin structure."""


async def get_weather(city: str = "New York") -> str:
    """Get weather for a city (simulated)."""
    return f"Weather in {city}: 72F, Partly Cloudy (simulated - connect a weather API)"


def register(tool_registry):
    """Register plugin tools with the tool registry."""
    tool_registry.register(
        "get_weather",
        "Get weather information for a city",
        get_weather,
        permission="free",
        params={"city": "City name"},
    )
