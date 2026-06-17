.PHONY: up down logs build clean test lint pull status restart backend-shell frontend-shell db-shell backup

# Primary Commands
up:
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

build:
	docker compose build --no-cache

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Service Logs
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-chromadb:
	docker compose logs -f chromadb

logs-redis:
	docker compose logs -f redis

# Development
backend-shell:
	docker compose exec backend bash

frontend-shell:
	docker compose exec frontend sh

# Testing
test:
	docker compose exec backend pytest tests/ -v

test-security:
	docker compose exec backend pytest tests/test_security.py -v

selftest:
	curl -s -X POST http://localhost:8200/api/selftest/run | python -m json.tool

# Linting
lint:
	docker compose exec backend ruff check .
	docker compose exec backend ruff format --check .

format:
	docker compose exec backend ruff format .

# Model Management
pull:
	ollama pull phi3:mini
	ollama pull llama3.1:8b

pull-all:
	ollama pull phi3:mini
	ollama pull llama3.1:8b
	ollama pull hermes3:latest
	ollama pull qwen2.5:14b

# Status
status:
	docker compose ps
	@echo ""
	@echo "--- Service Health ---"
	@curl -s http://localhost:8200/health 2>/dev/null || echo "Backend: DOWN"
	@echo ""
	@curl -s http://localhost:8400/api/v1/heartbeat 2>/dev/null || echo "ChromaDB: DOWN"
	@echo ""
	@docker compose exec redis redis-cli ping 2>/dev/null || echo "Redis: DOWN"

# Backup
backup:
	./scripts/backup.sh

# GPU Mode
up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d

# Quick Health Check
health:
	@curl -s http://localhost:8200/health | python -m json.tool
