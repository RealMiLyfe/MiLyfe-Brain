# MiLyfe Brain Python SDK

Official Python client for the MiLyfe Brain AI Agent Platform.

## Installation

```bash
pip install milyfe-brain
```

## Quick Start

```python
from milyfe_brain import MiLyfeBrainClient, AgentRole

# Initialize client
client = MiLyfeBrainClient("http://localhost:8200")

# Check health
health = client.health()
print(f"Status: {health.status}")

# Create and execute a playbook
playbook = client.create_playbook(
    title="Build a REST API",
    description="Create a FastAPI REST API with CRUD endpoints for a todo app"
)
print(f"Playbook {playbook.id}: {playbook.status}")

# Chat with the AI
response = client.chat("Explain how the agent swarm works")
print(response.content)

# Spawn a specific agent
agent = client.spawn_agent(AgentRole.CODER, "Write unit tests for auth module")
print(f"Agent {agent.name} spawned")
```

## Async Usage

```python
import asyncio
from milyfe_brain import MiLyfeBrainClient

async def main():
    async with MiLyfeBrainClient("http://localhost:8200") as client:
        # Stream real-time events
        async for event in client.stream_events_async():
            print(f"[{event.event_type}] {event.data}")

asyncio.run(main())
```

## API Reference

See [full documentation](https://github.com/RealMiLyfe/MiLyfe-Brain/blob/main/docs/api/openapi.yaml).
