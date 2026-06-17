# MiLyfe Brain Plugin SDK Documentation

Build custom plugins to extend MiLyfe Brain with new tools, integrations, and capabilities.

## Overview

Plugins allow you to:
- Add new tools that agents can use
- Integrate with external services
- Define custom agent behaviors
- Add new slash commands
- Extend the UI with custom panels

## Quick Start

```bash
# Create a new plugin
mkdir -p ~/.milyfe/plugins/my-plugin
cd ~/.milyfe/plugins/my-plugin

# Create the manifest
cat > manifest.json << 'EOF'
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My custom plugin",
  "author": "Your Name",
  "tools": ["my_tool"],
  "entry": "plugin.py"
}
EOF

# Create the plugin
cat > plugin.py << 'EOF'
from milyfe_brain.plugins import PluginBase, tool

class MyPlugin(PluginBase):
    @tool(name="my_tool", description="Does something useful")
    async def my_tool(self, input_text: str) -> str:
        return f"Processed: {input_text}"
EOF
```

## Architecture

```
~/.milyfe/plugins/
├── my-plugin/
│   ├── manifest.json    # Plugin metadata
│   ├── plugin.py        # Plugin implementation
│   ├── requirements.txt # Optional dependencies
│   └── assets/          # Optional static assets
└── another-plugin/
    └── ...
```

## Table of Contents

1. [Plugin Manifest](./manifest.md)
2. [Tool Development](./tools.md)
3. [Hooks & Middleware](./hooks.md)
4. [Configuration](./configuration.md)
5. [Testing Plugins](./testing.md)
6. [Publishing](./publishing.md)
7. [API Reference](./api-reference.md)
8. [Examples](./examples.md)
