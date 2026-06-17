# Contributing to MiLyfe Brain

Thank you for your interest in contributing! MiLyfe Brain is a community-driven project and we welcome contributions of all kinds.

---

## Quick Start for Contributors

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/MiLyfe-Brain.git
cd MiLyfe-Brain

# 2. Start infrastructure
docker compose up chromadb redis -d

# 3. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run backend (development mode)
uvicorn main:app --reload --port 8200

# 5. Frontend setup (separate terminal)
cd frontend
npm install
npm run dev

# 6. Run tests
cd backend
pytest tests/ -v
```

---

## Project Structure

```
MiLyfe-Brain/
├── backend/           # FastAPI + Python 3.11
│   ├── agents/        # AI Agent System (BaseAgent, roles, TAOR engine)
│   ├── api/routes/    # 19 API route modules
│   ├── graphs/        # Orchestration (parser, executor, swarm patterns)
│   ├── memory/        # Database + ChromaDB vector store
│   ├── models/        # Pydantic schemas
│   ├── tools/         # 18 agent tools
│   ├── safety/        # Permissions, classifier, audit
│   ├── services/      # 25+ background services
│   ├── prompts/       # Rule loader, skills, output styles
│   ├── hooks/         # Pre/post tool middleware
│   ├── mcp/           # Model Context Protocol
│   ├── plugins/       # Plugin system
│   └── tests/         # Test suite
├── frontend/          # Next.js 15 + React 19
│   └── src/
│       ├── app/       # Pages
│       ├── components/# UI components (9 views)
│       ├── hooks/     # Custom React hooks
│       └── lib/       # API client + Zustand store
├── docker-compose.yml # One-command deployment
├── Makefile           # Dev commands
└── FULL_SPEC.md       # Complete specification
```

---

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/RealMiLyfe/MiLyfe-Brain/issues) first
2. Include: steps to reproduce, expected vs actual behavior, system info (OS, Docker version, Ollama models)
3. Include logs: `make logs-backend` output if relevant

### Suggesting Features

1. Open a [Discussion](https://github.com/RealMiLyfe/MiLyfe-Brain/discussions) first
2. Describe the use case (WHY, not just WHAT)
3. Consider if it fits the [Manifesto](MANIFESTO.md) principles (local, free, private)

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes (see style guide below)
4. Add tests for new functionality
5. Run the test suite: `cd backend && pytest tests/ -v`
6. Commit with conventional format: `feat:`, `fix:`, `docs:`, `refactor:`
7. Push and open a Pull Request

---

## Code Style

### Python (Backend)

- **Formatter**: Ruff (`ruff format`)
- **Linter**: Ruff (`ruff check`)
- **Type hints**: Required for all public functions
- **Docstrings**: Required for all modules, classes, and public functions
- **Async**: Use `async/await` for all I/O operations
- **Imports**: Sort with ruff (isort rules)
- **Line length**: 120 characters max

### TypeScript (Frontend)

- **Formatter**: Prettier (via ESLint)
- **Components**: Function components with explicit types
- **State**: Zustand for global state, `useState` for local
- **Naming**: PascalCase for components, camelCase for functions/variables
- **Styles**: Tailwind CSS utility classes (no CSS-in-JS)

### Commit Messages

```
feat: add voice input to chat interface
fix: prevent file_delete from escaping workspace sandbox
docs: add plugin development guide
refactor: extract tool execution into TAOR engine
test: add tests for playbook variable resolution
```

---

## Architecture Decisions

Before making significant changes, understand the key decisions:

1. **Pure httpx for LLM calls** — No langchain-ollama. Direct POST to Ollama /api/chat.
2. **Pure httpx for ChromaDB** — No chromadb Python client. Direct REST API.
3. **Single uvicorn worker** — Required for shared state (SQLite, daemon, agents).
4. **TAOR engine** — All agent execution goes through Think-Act-Observe-Repeat loop.
5. **Connection pooling** — Shared httpx client across all agents.
6. **Safety first** — All tool execution goes through permission check + pre/post hooks.

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

---

## Writing Plugins

```python
# plugins/my-plugin/manifest.json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "description": "What it does",
  "tools": ["my_tool_name"]
}

# plugins/my-plugin/plugin.py
from models.schemas import PermissionLevel

async def my_tool_name(arg1: str, arg2: int = 5) -> str:
    """Tool description shown to agents."""
    return f"Result: {arg1} * {arg2}"

def register(registry):
    registry.register(
        name="my_tool_name",
        handler=my_tool_name,
        category="Plugin",
        description="What this tool does",
        parameters={"arg1": "str", "arg2": "int"},
        permission=PermissionLevel.FREE,
    )
```

---

## Writing Skills

Skills auto-activate when input matches trigger keywords:

```yaml
# .milyfe/skills/my_skill.yaml
---
name: my_skill
triggers:
  - keyword1
  - keyword2
  - phrase to match
---
# Instructions injected when triggered

When working with [topic], always:
1. Do this first
2. Then do this
3. Never do this
```

---

## Testing

```bash
# Run all tests
cd backend && pytest tests/ -v

# Run specific test file
pytest tests/test_security.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run only fast tests (skip integration)
pytest tests/ -v -m "not integration"
```

### Writing Tests

- Place tests in `backend/tests/`
- Name files `test_*.py`
- Use `pytest` and `pytest-asyncio` for async tests
- Mock external services (Ollama, ChromaDB) in unit tests
- Test the contract, not the implementation

---

## Community

- **Discussions**: GitHub Discussions for questions, ideas, and support
- **Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
