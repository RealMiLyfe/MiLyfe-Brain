# Plugin Manifest

Every plugin requires a `manifest.json` file that describes its metadata and capabilities.

## Schema

```json
{
  "name": "string (required) - Unique plugin identifier",
  "version": "string (required) - Semver version",
  "description": "string (required) - Human-readable description",
  "author": "string (optional) - Author name or organization",
  "license": "string (optional) - License identifier (e.g., MIT)",
  "homepage": "string (optional) - URL to plugin documentation",
  "entry": "string (required) - Main Python file (relative path)",
  "tools": ["array of tool names this plugin registers"],
  "hooks": {
    "pre_tool": ["hook names"],
    "post_tool": ["hook names"]
  },
  "permissions": ["file_read", "file_write", "shell_exec", "network"],
  "config_schema": {
    "api_key": {"type": "string", "required": true, "secret": true},
    "endpoint": {"type": "string", "default": "https://api.example.com"}
  },
  "dependencies": ["pip package names"],
  "min_brain_version": "2.0.0",
  "tags": ["category", "tags", "for", "discovery"]
}
```

## Example

```json
{
  "name": "weather-plugin",
  "version": "1.0.0",
  "description": "Get weather information for any location",
  "author": "MiLyfe Team",
  "license": "MIT",
  "entry": "plugin.py",
  "tools": ["get_weather", "get_forecast"],
  "permissions": ["network"],
  "config_schema": {
    "api_key": {
      "type": "string",
      "required": true,
      "secret": true,
      "description": "OpenWeatherMap API key"
    },
    "units": {
      "type": "string",
      "default": "metric",
      "enum": ["metric", "imperial"]
    }
  },
  "dependencies": ["httpx"],
  "min_brain_version": "2.0.0",
  "tags": ["weather", "utility", "external-api"]
}
```

## Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique kebab-case identifier |
| `version` | string | Yes | Semantic version (X.Y.Z) |
| `description` | string | Yes | One-line description |
| `entry` | string | Yes | Path to main Python module |
| `tools` | string[] | Yes | Tool names registered by this plugin |
| `permissions` | string[] | No | Required permission types |
| `config_schema` | object | No | Configuration fields with types |
| `dependencies` | string[] | No | pip packages to install |
| `min_brain_version` | string | No | Minimum compatible Brain version |
