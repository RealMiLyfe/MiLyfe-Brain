# Tool Development

Tools are the primary way plugins extend MiLyfe Brain's capabilities. Each tool is a function that agents can invoke during task execution.

## Basic Tool

```python
from milyfe_brain.plugins import PluginBase, tool

class MyPlugin(PluginBase):

    @tool(
        name="calculate",
        description="Perform a mathematical calculation",
        parameters={
            "expression": {"type": "string", "description": "Math expression to evaluate"},
        }
    )
    async def calculate(self, expression: str) -> str:
        """Safely evaluate a math expression."""
        # Only allow safe math operations
        allowed = set("0123456789+-*/().^ ")
        if not all(c in allowed for c in expression):
            return "Error: Invalid characters in expression"
        try:
            result = eval(expression)  # Safe because we validated input
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"
```

## Tool Decorator Options

```python
@tool(
    name="tool_name",              # Required: unique tool identifier
    description="What it does",     # Required: shown to agents
    parameters={...},               # Required: input schema
    permission="notify",            # Optional: free|notify|approve|blocked
    category="utility",             # Optional: grouping category
    timeout=30,                     # Optional: max execution time (seconds)
    cacheable=True,                 # Optional: cache results
    rate_limit=10,                  # Optional: max calls per minute
)
```

## Parameter Types

```python
parameters = {
    "text": {
        "type": "string",
        "description": "Input text",
        "required": True,
        "max_length": 10000,
    },
    "count": {
        "type": "integer",
        "description": "Number of items",
        "default": 5,
        "minimum": 1,
        "maximum": 100,
    },
    "enabled": {
        "type": "boolean",
        "description": "Enable feature",
        "default": True,
    },
    "options": {
        "type": "string",
        "description": "Select option",
        "enum": ["option_a", "option_b", "option_c"],
    },
    "files": {
        "type": "array",
        "description": "List of file paths",
        "items": {"type": "string"},
    },
}
```

## Accessing Plugin Config

```python
class MyPlugin(PluginBase):

    async def on_load(self):
        """Called when plugin is loaded."""
        self.api_key = self.config.get("api_key")
        self.endpoint = self.config.get("endpoint", "https://default.api.com")

    @tool(name="fetch_data", description="Fetch data from API")
    async def fetch_data(self, query: str) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.endpoint}/search",
                params={"q": query},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return resp.text
```

## Tool Return Types

Tools should return strings. Complex data should be JSON-serialized:

```python
import json

@tool(name="get_users", description="List users")
async def get_users(self) -> str:
    users = [{"name": "Alice", "role": "admin"}, {"name": "Bob", "role": "user"}]
    return json.dumps(users, indent=2)
```

## Error Handling

```python
@tool(name="risky_operation", description="May fail")
async def risky_operation(self, path: str) -> str:
    try:
        result = await self.do_something(path)
        return f"Success: {result}"
    except FileNotFoundError:
        return "Error: File not found"
    except PermissionError:
        return "Error: Permission denied"
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        return f"Error: {str(e)}"
```

## Lifecycle Methods

```python
class MyPlugin(PluginBase):

    async def on_load(self):
        """Called when plugin is loaded. Initialize resources here."""
        self.client = httpx.AsyncClient()

    async def on_unload(self):
        """Called when plugin is unloaded. Cleanup resources."""
        await self.client.aclose()

    async def on_config_change(self, key: str, value: any):
        """Called when configuration changes at runtime."""
        if key == "endpoint":
            self.endpoint = value
```
