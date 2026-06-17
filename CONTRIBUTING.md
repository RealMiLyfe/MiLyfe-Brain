# Contributing to MiLyfe Brain

Thank you for your interest in contributing! MiLyfe Brain is a community-driven project and we welcome contributions of all kinds — bug fixes, features, documentation, plugins, and skills.

---

## Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/MiLyfe-Brain.git
cd MiLyfe-Brain

# 2. Copy environment config
cp .env.example .env

# 3. Start all services
docker compose up --build -d

# 4. Verify everything is running
make health

# 5. Run tests
make test
```

---

## Project Structure

```
MiLyfe-Brain/
├── backend/                 # FastAPI (Python 3.11)
│   ├── agents/              # Agent swarm system (base, roles, factory, bus)
│   ├── api/routes/          # 19 REST API route modules
│   ├── graphs/              # Orchestration engine (parser, executor, swarm)
│   ├── memory/              # SQLite + ChromaDB + checkpointer
│   ├── tools/               # 18 tool implementations
│   ├── safety/              # Permissions, approvals, classifier, audit
│   ├── services/            # 20+ background services
│   ├── prompts/             # Rule loader, slash commands, output styles
│   ├── plugins/             # Plugin loader + examples
│   ├── hooks/               # Pre/post tool middleware
│   ├── mcp/                 # Model Context Protocol (server + client)
│   ├── models/schemas.py    # Pydantic data models
│   └── tests/               # Pytest test suite
├── frontend/                # Next.js 15 + React 19 + TypeScript
│   └── src/
│       ├── app/             # App router (layout, pages)
│       ├── components/      # UI components (9 panel groups)
│       ├── lib/             # API client + Zustand store
│       └── hooks/           # Custom React hooks
├── examples/                # Example playbook files
└── scripts/                 # Utility scripts (backup, etc.)
```

---

## Code Style

### Python (Backend)

- **Linter/Formatter:** [Ruff](https://docs.astral.sh/ruff/)
- **Type hints:** Required on all public functions
- **Docstrings:** Required on modules, classes, and public functions
- **Line length:** 100 characters
- **Imports:** Sorted by ruff (isort-compatible)

```bash
make lint       # Check with ruff
make format     # Auto-format with ruff
```

### TypeScript (Frontend)

- **Linter:** ESLint with Next.js config
- **Formatter:** Prettier
- **Strict mode:** Enabled in `tsconfig.json`
- **Components:** Functional components with TypeScript interfaces

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

**Scopes:** `agents`, `api`, `tools`, `memory`, `safety`, `frontend`, `cli`, `plugins`, `infra`

**Examples:**
```
feat(agents): add debate swarm pattern for critic role
fix(tools): handle timeout in shell_exec gracefully
docs(readme): update quick start for GPU users
test(safety): add command injection detection tests
```

---

## Writing Plugins

Plugins live in `backend/plugins/` and are auto-discovered at startup.

```
backend/plugins/my-plugin/
├── manifest.json       # Plugin metadata and tool declarations
└── plugin.py           # Tool implementation functions
```

**manifest.json:**
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "tools": [
    {
      "name": "my_tool",
      "description": "Tool description for the LLM",
      "parameters": {
        "input": { "type": "string", "description": "Input value" }
      }
    }
  ]
}
```

**plugin.py:**
```python
async def my_tool(input: str) -> str:
    """Tool implementation. Must match the name in manifest.json."""
    return f"Processed: {input}"
```

---

## Writing Skills

Skills auto-activate when user input matches their triggers.

Place custom skills in `~/.milyfe/skills/` or `<workspace>/.milyfe/skills/`:

```yaml
# my_skill.yaml
name: my_skill
description: When to use this skill
triggers:
  - keyword1
  - keyword2
instructions: |
  When this skill activates, follow these guidelines:
  - Guideline 1
  - Guideline 2
```

Skills are injected into the agent's prompt context when trigger relevance exceeds the 0.3 threshold.

---

## Testing

```bash
# Run full test suite with coverage
make test

# Run specific test file
docker compose exec backend pytest tests/test_security.py -v

# Run tests matching a pattern
docker compose exec backend pytest -k "test_path_traversal" -v

# Run self-test (E2E connectivity check)
make selftest
```

**Writing tests:**
- Place tests in `backend/tests/`
- Use `conftest.py` fixtures for common setup
- Name files `test_*.py`, functions `test_*`
- Mock external services (Ollama, ChromaDB) in unit tests
- Use `httpx.AsyncClient` with FastAPI's `TestClient` for API tests

---

## Pull Request Guidelines

1. **Branch from `main`** — Create a feature branch: `feat/my-feature` or `fix/issue-description`
2. **Keep PRs focused** — One feature or fix per PR
3. **Include tests** — New features need tests; bug fixes need regression tests
4. **Update docs** — If your change affects the API or user-facing behavior
5. **Run checks locally** — `make lint && make test` before pushing
6. **Write a clear description** — What, why, and how to test
7. **Link issues** — Reference related issues with `Closes #123`

### PR Checklist

- [ ] Code follows project style (ruff/eslint pass)
- [ ] Tests pass locally (`make test`)
- [ ] New functionality has tests
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format
- [ ] No secrets or credentials in code

---

## Need Help?

- Check existing issues for similar questions
- Open a discussion for architecture questions
- File an issue for bugs with reproduction steps

Welcome aboard — every contribution makes AI more accessible.
