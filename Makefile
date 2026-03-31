.PHONY: help setup dev-up dev-down test lint format clean

help:
	@echo "TradeSense Development Commands"
	@echo "================================"
	@echo "setup          - Initial project setup"
	@echo "dev-up         - Start development environment"
	@echo "dev-down       - Stop development environment"
	@echo "test           - Run all tests"
	@echo "lint           - Run linters"
	@echo "format         - Format code"
	@echo "clean          - Clean up generated files"

setup:
	@echo "Setting up TradeSense development environment..."
	cp .env.example .env
	@echo "✓ Created .env file"
	cd backend && pip install -r requirements.txt
	@echo "✓ Installed Python dependencies"
	cd frontend && npm install
	@echo "✓ Installed TypeScript dependencies"
	@echo "✓ Setup complete! Edit .env with your configuration, then run 'make dev-up'"

dev-up:
	@echo "Starting development environment..."
	docker-compose -f docker/compose/docker-compose.dev.yml up -d
	@echo "✓ Infrastructure services started"
	@echo "Waiting for services to be healthy..."
	sleep 10
	@echo "✓ Development environment ready!"
	@echo ""
	@echo "Services:"
	@echo "  PostgreSQL:  localhost:5432"
	@echo "  Redis:       localhost:6379"
	@echo "  Ollama:      localhost:11434"
	@echo "  InvenTree:   localhost:8080"
	@echo "  Langfuse:    localhost:3000"
	@echo "  Phoenix:     localhost:6006"
	@echo "  Prometheus:  localhost:9090"
	@echo "  Grafana:     localhost:3001"

dev-down:
	@echo "Stopping development environment..."
	docker-compose -f docker/compose/docker-compose.dev.yml down
	@echo "✓ Development environment stopped"

test:
	@echo "Running tests..."
	cd backend && pytest tests/ -v --cov=. --cov-report=html
	@echo "✓ Tests complete"

lint:
	@echo "Running linters..."
	cd backend && flake8 . && mypy .
	cd frontend && npm run lint
	@echo "✓ Linting complete"

format:
	@echo "Formatting code..."
	cd backend && black . && isort .
	cd frontend && npm run format
	@echo "✓ Formatting complete"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.cache
	@echo "✓ Cleanup complete"
