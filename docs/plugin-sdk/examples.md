# Plugin Examples

## Example 1: Weather Plugin

```python
# plugins/weather/plugin.py
import json
import httpx
from milyfe_brain.plugins import PluginBase, tool

class WeatherPlugin(PluginBase):
    """Provides weather information to agents."""

    async def on_load(self):
        self.api_key = self.config["api_key"]
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.client = httpx.AsyncClient()

    async def on_unload(self):
        await self.client.aclose()

    @tool(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
            "location": {"type": "string", "description": "City name or coordinates"},
            "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"},
        },
        permission="free",
    )
    async def get_weather(self, location: str, units: str = "metric") -> str:
        resp = await self.client.get(f"{self.base_url}/weather", params={
            "q": location, "appid": self.api_key, "units": units,
        })
        if resp.status_code != 200:
            return f"Error: Could not get weather for {location}"
        data = resp.json()
        return json.dumps({
            "location": data["name"],
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
        }, indent=2)

    @tool(
        name="get_forecast",
        description="Get 5-day weather forecast",
        parameters={
            "location": {"type": "string", "description": "City name"},
        },
    )
    async def get_forecast(self, location: str) -> str:
        resp = await self.client.get(f"{self.base_url}/forecast", params={
            "q": location, "appid": self.api_key, "units": "metric", "cnt": 5,
        })
        if resp.status_code != 200:
            return f"Error: Could not get forecast for {location}"
        data = resp.json()
        forecasts = [
            {"date": item["dt_txt"], "temp": item["main"]["temp"],
             "description": item["weather"][0]["description"]}
            for item in data["list"]
        ]
        return json.dumps(forecasts, indent=2)
```

## Example 2: Database Query Plugin

```python
# plugins/db-query/plugin.py
import json
import sqlite3
from milyfe_brain.plugins import PluginBase, tool

class DatabasePlugin(PluginBase):
    """Query databases safely."""

    @tool(
        name="query_db",
        description="Execute a read-only SQL query",
        parameters={
            "query": {"type": "string", "description": "SQL SELECT query"},
            "database": {"type": "string", "description": "Database file path"},
        },
        permission="notify",
    )
    async def query_db(self, query: str, database: str = "/data/milyfe.db") -> str:
        # Safety: only allow SELECT
        if not query.strip().upper().startswith("SELECT"):
            return "Error: Only SELECT queries are allowed"

        try:
            conn = sqlite3.connect(database)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            rows = [dict(row) for row in cursor.fetchmany(100)]
            conn.close()
            return json.dumps({"rows": rows, "count": len(rows)}, indent=2, default=str)
        except Exception as e:
            return f"Error: {e}"
```

## Example 3: Notification Plugin

```python
# plugins/slack-notify/plugin.py
import httpx
from milyfe_brain.plugins import PluginBase, tool, hook

class SlackNotifyPlugin(PluginBase):
    """Send notifications to Slack."""

    async def on_load(self):
        self.webhook_url = self.config["webhook_url"]
        self.client = httpx.AsyncClient()

    @tool(
        name="notify_slack",
        description="Send a message to Slack channel",
        parameters={
            "message": {"type": "string", "description": "Message to send"},
            "channel": {"type": "string", "description": "Channel name", "default": "#general"},
        },
        permission="notify",
    )
    async def notify_slack(self, message: str, channel: str = "#general") -> str:
        resp = await self.client.post(self.webhook_url, json={
            "channel": channel,
            "text": message,
            "username": "MiLyfe Brain",
            "icon_emoji": ":brain:",
        })
        if resp.status_code == 200:
            return f"Message sent to {channel}"
        return f"Error: Slack returned {resp.status_code}"

    @hook("post_tool")
    async def notify_on_completion(self, tool_name: str, params: dict, result: str) -> str:
        """Notify Slack when playbook completes."""
        if tool_name == "playbook_complete":
            await self.notify_slack(f"Playbook completed: {params.get('title', 'Unknown')}")
        return result
```

## Example 4: Code Quality Plugin

```python
# plugins/code-quality/plugin.py
import subprocess
import json
from milyfe_brain.plugins import PluginBase, tool

class CodeQualityPlugin(PluginBase):
    """Code quality analysis tools."""

    @tool(
        name="lint_python",
        description="Run ruff linter on a Python file",
        parameters={
            "file_path": {"type": "string", "description": "Path to Python file"},
        },
        permission="free",
    )
    async def lint_python(self, file_path: str) -> str:
        try:
            result = subprocess.run(
                ["ruff", "check", file_path, "--format", "json"],
                capture_output=True, text=True, timeout=30,
            )
            issues = json.loads(result.stdout) if result.stdout else []
            if not issues:
                return "No linting issues found!"
            summary = [f"Line {i['location']['row']}: {i['message']} [{i['code']}]" for i in issues[:10]]
            return f"Found {len(issues)} issues:\n" + "\n".join(summary)
        except Exception as e:
            return f"Error running linter: {e}"

    @tool(
        name="complexity_check",
        description="Check code complexity metrics",
        parameters={
            "file_path": {"type": "string", "description": "Path to file"},
        },
    )
    async def complexity_check(self, file_path: str) -> str:
        try:
            result = subprocess.run(
                ["radon", "cc", file_path, "-j"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout or "No complexity data available"
        except FileNotFoundError:
            return "Error: radon not installed (pip install radon)"
```
