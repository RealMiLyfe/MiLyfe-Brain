.PHONY: up down build logs restart clean test lint format health selftest gpu

# Default target
up:
	docker compose up -d

# Build and start
build:
	docker compose up --build -d

# GPU mode (AMD ROCm)
gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Backend logs only
logs-backend:
	docker compose logs -f backend

# Frontend logs only
logs-frontend:
	docker compose logs -f frontend

# Restart all
restart:
	docker compose restart

# Restart backend only
restart-backend:
	docker compose restart backend

# Clean everything (including volumes)
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Run backend tests
test:
	docker compose exec backend pytest -v

# Run linting
lint:
	docker compose exec backend ruff check .
	cd frontend && npx eslint .

# Format code
format:
	docker compose exec backend ruff format .

# Health check
health:
	@curl -s http://localhost:8200/health | python3 -m json.tool

# Run self-test
selftest:
	@curl -s -X POST http://localhost:8200/api/selftest/run | python3 -m json.tool

# Backup
backup:
	./scripts/backup.sh

# Shell into backend
shell:
	docker compose exec backend bash

# Shell into frontend
shell-frontend:
	docker compose exec frontend sh

# Status
status:
	docker compose ps
