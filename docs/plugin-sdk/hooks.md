# Hooks & Middleware

Hooks allow plugins to intercept and modify tool execution at various points in the pipeline.

## Hook Types

| Hook | Timing | Use Case |
|------|--------|----------|
| `pre_tool` | Before tool execution | Validate, modify params, block |
| `post_tool` | After tool execution | Transform output, log, cache |
| `pre_llm` | Before LLM call | Modify prompt, add context |
| `post_llm` | After LLM response | Filter, validate, enrich |
| `on_agent_spawn` | Agent creation | Inject context, configure |
| `on_agent_retire` | Agent completion | Cleanup, persist learnings |

## Pre-Tool Hook

```python
from milyfe_brain.plugins import PluginBase, hook

class SecurityPlugin(PluginBase):

    @hook("pre_tool")
    async def validate_file_paths(self, tool_name: str, params: dict) -> dict:
        """Validate all file paths before execution."""
        if tool_name in ("file_read", "file_write", "file_delete"):
            path = params.get("path", "")
            if ".." in path or path.startswith("/etc"):
                raise PermissionError(f"Access denied: {path}")
        return params  # Return (possibly modified) params

    @hook("pre_tool")
    async def rate_limit_check(self, tool_name: str, params: dict) -> dict:
        """Enforce per-tool rate limits."""
        key = f"rate:{tool_name}"
        count = await self.cache.incr(key)
        if count > self.config.get("max_calls_per_minute", 60):
            raise RuntimeError(f"Rate limit exceeded for {tool_name}")
        return params
```

## Post-Tool Hook

```python
class AuditPlugin(PluginBase):

    @hook("post_tool")
    async def audit_log(self, tool_name: str, params: dict, result: str) -> str:
        """Log all tool executions for compliance."""
        await self.store_audit_event({
            "tool": tool_name,
            "params": params,
            "result_length": len(result),
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.context.agent_id,
        })
        return result  # Return (possibly modified) result

    @hook("post_tool")
    async def truncate_large_output(self, tool_name: str, params: dict, result: str) -> str:
        """Truncate excessively large tool outputs."""
        max_length = self.config.get("max_output_length", 50000)
        if len(result) > max_length:
            return result[:max_length] + f"\n\n[Truncated: {len(result)} → {max_length} chars]"
        return result
```

## Pre-LLM Hook

```python
class ContextPlugin(PluginBase):

    @hook("pre_llm")
    async def inject_project_context(self, messages: list, model: str) -> list:
        """Add project-specific context to every LLM call."""
        project_rules = await self.load_project_rules()
        if project_rules:
            # Inject as system message
            context_msg = {
                "role": "system",
                "content": f"Project rules:\n{project_rules}"
            }
            messages.insert(1, context_msg)
        return messages
```

## Hook Priority

Hooks execute in priority order (lower number = earlier):

```python
@hook("pre_tool", priority=1)  # Runs first
async def security_check(self, ...): ...

@hook("pre_tool", priority=10)  # Runs after security
async def logging_hook(self, ...): ...

@hook("pre_tool", priority=100)  # Runs last
async def transform_params(self, ...): ...
```

## Blocking Execution

Pre-hooks can block execution by raising an exception:

```python
@hook("pre_tool")
async def block_dangerous(self, tool_name: str, params: dict) -> dict:
    if tool_name == "shell_exec":
        cmd = params.get("command", "")
        if "rm -rf" in cmd:
            raise PermissionError("Blocked: destructive shell command")
    return params
```
