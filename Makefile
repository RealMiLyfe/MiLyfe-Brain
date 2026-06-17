.PHONY: up build gpu down logs logs-backend logs-frontend restart clean test lint format health selftest backup shell shell-frontend status

# Default target
up:
	docker compose up -d

build:
	docker compose build

gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

restart:
	docker compose restart

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

test:
	docker compose exec backend pytest --cov=. --cov-report=term-missing -v

lint:
	docker compose exec backend ruff check .

format:
	docker compose exec backend ruff format .

health:
	@echo "--- Backend Health ---"
	@curl -sf http://localhost:8200/health | python3 -m json.tool || echo "Backend unhealthy"
	@echo ""
	@echo "--- Redis ---"
	@docker compose exec redis redis-cli ping || echo "Redis unhealthy"
	@echo ""
	@echo "--- ChromaDB ---"
	@curl -sf http://localhost:8400/api/v1/heartbeat | python3 -m json.tool || echo "ChromaDB unhealthy"

selftest:
	@echo "Running self-test suite..."
	docker compose exec backend pytest tests/ -v --tb=short
	@echo "Self-test complete."

backup:
	@bash scripts/backup.sh

shell:
	docker compose exec backend /bin/bash

shell-frontend:
	docker compose exec frontend /bin/sh

status:
	@echo "=== MiLyfe Brain Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Resource Usage ==="
	@docker compose top
