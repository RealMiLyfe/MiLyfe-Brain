# ═══════════════════════════════════════════════════════════════════════════════
# MiLyfe Brain — Development & Deployment Makefile
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: up down logs build clean test lint shell db-migrate seed help

COMPOSE := docker compose
GPU_COMPOSE := $(COMPOSE) -f docker-compose.yml -f docker-compose.gpu.yml

# Default target
help: ## Show this help message
	@echo "MiLyfe Brain — Available Commands"
	@echo "══════════════════════════════════════════════════════"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker Compose ───────────────────────────────────────────────────────────

up: ## Start all services (detached)
	$(COMPOSE) up -d
	@echo "\n✅ MiLyfe Brain is running!"
	@echo "   Backend:  http://localhost:8200"
	@echo "   Frontend: http://localhost:3000"
	@echo "   ChromaDB: http://localhost:8400"
	@echo "   API Docs: http://localhost:8200/docs"

up-gpu: ## Start all services with AMD ROCm GPU support
	$(GPU_COMPOSE) up -d
	@echo "\n✅ MiLyfe Brain (GPU) is running!"
	@echo "   Ollama:   http://localhost:11434"

down: ## Stop all services
	$(COMPOSE) down
	@echo "🛑 All services stopped."

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-backend: ## Tail backend logs only
	$(COMPOSE) logs -f --tail=100 backend

build: ## Rebuild all Docker images
	$(COMPOSE) build --no-cache
	@echo "🔨 Build complete."

clean: ## Stop services, remove volumes, and prune images
	$(COMPOSE) down -v --remove-orphans
	docker image prune -f
	@echo "🧹 Cleaned up containers, volumes, and dangling images."

# ─── Development ──────────────────────────────────────────────────────────────

test: ## Run the test suite
	cd backend && python -m pytest tests/ -v --tb=short --asyncio-mode=auto
	@echo "\n✅ Tests complete."

test-cov: ## Run tests with coverage report
	cd backend && python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term --asyncio-mode=auto
	@echo "\n📊 Coverage report at backend/htmlcov/index.html"

lint: ## Run linters (Ruff for Python, ESLint for frontend)
	@echo "🔍 Linting Python..."
	cd backend && ruff check . --fix
	cd backend && ruff format .
	@echo "🔍 Linting Frontend..."
	cd frontend && npx eslint . --fix 2>/dev/null || echo "  (ESLint not configured or frontend not built)"
	@echo "\n✅ Linting complete."

shell: ## Open a shell in the backend container
	$(COMPOSE) exec backend /bin/bash

shell-db: ## Open a SQLite shell for the database
	$(COMPOSE) exec backend sqlite3 /data/milyfe.db

# ─── Database ─────────────────────────────────────────────────────────────────

db-migrate: ## Run Alembic database migrations
	$(COMPOSE) exec backend alembic upgrade head
	@echo "✅ Migrations applied."

db-revision: ## Create a new Alembic migration (usage: make db-revision MSG="description")
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed the database with sample data
	$(COMPOSE) exec backend python -c "\
		import asyncio; \
		from memory.database import init_db; \
		asyncio.run(init_db()); \
		print('✅ Database seeded.')"

# ─── Utilities ────────────────────────────────────────────────────────────────

status: ## Show running containers and their status
	$(COMPOSE) ps

restart: ## Restart all services
	$(COMPOSE) restart
	@echo "🔄 Services restarted."

restart-backend: ## Restart backend only
	$(COMPOSE) restart backend

pull: ## Pull latest images
	$(COMPOSE) pull

env: ## Create .env from example if it doesn't exist
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📋 Created .env from .env.example — please review and update."; \
	else \
		echo "ℹ️  .env already exists. Skipping."; \
	fi
