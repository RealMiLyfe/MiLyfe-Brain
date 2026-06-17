# Contributing to MiLyfe Brain

Thank you for considering contributing to MiLyfe Brain! This document provides guidelines for development setup, coding standards, and the PR process.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Ollama (for LLM integration testing)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install ruff mypy pytest pytest-asyncio pytest-cov

# Run locally
uvicorn main:app --host 0.0.0.0 --port 8200 --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
python -m pytest tests/ -v --asyncio-mode=auto
```

## Coding Standards

### Python (Backend)

- **Formatter/Linter:** Ruff (configured in `pyproject.toml`)
- **Type hints:** Required on all public functions
- **Docstrings:** Google style, required on all public classes/functions
- **Async:** Use `async/await` for all I/O operations
- **Imports:** Relative within the backend (e.g., `from config import settings`)

```bash
# Format and lint
cd backend
ruff check . --fix
ruff format .
```

### TypeScript (Frontend)

- **Strict mode:** Enabled in `tsconfig.json`
- **Components:** Functional with hooks, no class components
- **State:** Zustand for global, React state for local
- **Styling:** Tailwind CSS utility classes

## Architecture Guidelines

### Adding a New Tool

1. Create `backend/tools/my_tool.py` with async handler functions
2. Add imports to `backend/tools/__init__.py`
3. Register in `register_all_tools()` with appropriate permission level
4. Add tests in `backend/tests/test_my_tool.py`

### Adding a New API Route

1. Create `backend/api/routes/my_route.py` with FastAPI router
2. Add import and `app.include_router()` in `backend/main.py`
3. Use Pydantic models from `backend/models/schemas.py`
4. Add tests

### Adding a New Service

1. Create `backend/services/my_service.py`
2. Use singleton pattern (module-level instance)
3. Initialize in `main.py` lifespan if needed at startup
4. Handle failures gracefully (try/except, non-fatal)

## Pull Request Process

1. Create a feature branch from `enterprise-complete`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass: `make test`
4. Ensure linting passes: `make lint`
5. Update documentation if needed
6. Open a PR with a clear description of changes
7. Wait for review

### Commit Messages

Follow conventional commits:

```
feat(scope): Add new feature
fix(scope): Fix a bug
test(scope): Add or update tests
docs(scope): Documentation changes
refactor(scope): Code refactoring
chore(scope): Build/config changes
```

### PR Checklist

- [ ] Tests pass locally
- [ ] New code has tests
- [ ] No `from backend.X` imports (use `from X`)
- [ ] Async functions use `await` for all I/O
- [ ] Error handling follows graceful degradation pattern
- [ ] New tools registered with appropriate permission level

## Code of Conduct

Be respectful, collaborative, and constructive. We're building something cool together.
